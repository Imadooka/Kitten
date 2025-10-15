from django.shortcuts import render, redirect, get_object_or_404
from .models import Ingredient, IngredientImage
from datetime import date , timedelta , datetime 
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
import json 
from django.conf import settings
from django.db.models import Q
from datetime import date as _date
from django.utils import timezone

with open("index/thai_alias.json", "r", encoding="utf-8") as f:
    TH_EN = json.load(f)


def index(request):
    ingredients = Ingredient.objects.all().order_by('prepared_date')
    latest_ingredients = Ingredient.objects.order_by('-created_at')[:4]  
    return render(request, 'main.html', {'ingredients': ingredients, 'latest_ingredients': latest_ingredients})

def delete_ingredient(request, ingredient_id):
    if request.method == "POST":
        ing = get_object_or_404(Ingredient, id=ingredient_id)
        ing.delete()
    return redirect('index')

def add_ingredient(request):
    today = date.today().isoformat()
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        quantity = int(request.POST.get("quantity", 1))
        prepared_s = request.POST.get("prepared_date")
        expiry_s = request.POST.get("expiry_date")

        if not name or not prepared_s or not expiry_s:
            return redirect('index')

        prepared_dt = date.fromisoformat(prepared_s)
        expiry_dt = date.fromisoformat(expiry_s)

        # อัปโหลด/อัปเดตรูป
        image_file = request.FILES.get("image_file")
        image_obj = None
        if image_file:
            img, _ = IngredientImage.objects.get_or_create(name=name)
            img.image = image_file
            img.save()
            image_obj = img

        # รวมกับรายการเดิมชื่อเดียวกัน
        existing = Ingredient.objects.filter(name__iexact=name).order_by('created_at').first()
        if existing:
            new_qty = existing.quantity + quantity
            min_prepared = min(existing.prepared_date, prepared_dt)
            min_expiry = min(existing.expiry_date, expiry_dt)
            new_shelf = (min_expiry - min_prepared).days

            existing.quantity = new_qty
            existing.prepared_date = min_prepared
            existing.shelf_life_days = new_shelf
            if image_obj:
                existing.image = image_obj
            existing.save()
        else:
            shelf_life_days = (expiry_dt - prepared_dt).days
            Ingredient.objects.create(
                name=name,
                quantity=quantity,
                prepared_date=prepared_dt,
                shelf_life_days=shelf_life_days,
                image=image_obj
            )
        return redirect('index')

    return render(request, 'add.html', {'today': today})

@require_POST
def voice_add_ingredient(request):
    """
    รับ JSON: {name, quantity, prepared_date, expiry_date}
    กติกาเดียวกับ add_ingredient (มีรวมรายการเดิม)
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        name = (data.get('name') or '').strip()
        quantity = int(data.get('quantity') or 1)
        prepared_s = data.get('prepared_date') or date.today().isoformat()
        expiry_s = data.get('expiry_date')

        if not name:
            return HttpResponseBadRequest('Missing name')
        if not expiry_s:
            expiry_s = (date.fromisoformat(prepared_s) + timedelta(days=7)).isoformat()

        prepared_dt = date.fromisoformat(prepared_s)
        expiry_dt = date.fromisoformat(expiry_s)

        existing = Ingredient.objects.filter(name__iexact=name).order_by('created_at').first()
        if existing:
            new_qty = existing.quantity + quantity
            min_prepared = min(existing.prepared_date, prepared_dt)
            min_expiry = min(existing.expiry_date, expiry_dt)
            new_shelf = (min_expiry - min_prepared).days

            existing.quantity = new_qty
            existing.prepared_date = min_prepared
            existing.shelf_life_days = new_shelf
            existing.save()
            return JsonResponse({'ok': True, 'id': existing.id, 'merged': True})
        else:
            shelf_life_days = (expiry_dt - prepared_dt).days
            ing = Ingredient.objects.create(
                name=name,
                quantity=quantity,
                prepared_date=prepared_dt,
                shelf_life_days=shelf_life_days,
            )
            return JsonResponse({'ok': True, 'id': ing.id, 'merged': False})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    
@require_POST
def voice_delete_ingredient(request):
    """
    รับ JSON: {"name": "นมสด", "amount": 2} หรือ {"name": "นมสด", "amount": "all"}
    คืน: {"ok": True, "name": "...", "deleted": n, "remaining": m, "deleted_all": bool}
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        name = (data.get("name") or "").strip()
        amount = data.get("amount", "").strip() if isinstance(data.get("amount"), str) else data.get("amount")

        if not name:
            return HttpResponseBadRequest("Missing name")

        ing = Ingredient.objects.filter(name__iexact=name).order_by("created_at").first()
        if not ing:
            return JsonResponse({"ok": False, "error": f"ไม่พบบันทึกชื่อ '{name}'"}, status=404)

        # แปลง amount
        delete_all = False
        if isinstance(amount, str) and amount.lower() in {"all", "ทั้งหมด"}:
            delete_all = True
        elif amount is None:
            # ถ้าไม่ได้ระบุจำนวน ถือว่า "ลบทั้งหมด"
            delete_all = True
        else:
            try:
                amount = int(amount)
            except Exception:
                return HttpResponseBadRequest("amount ต้องเป็นตัวเลขหรือ 'all'")

        if delete_all or amount >= ing.quantity:
            deleted = ing.quantity
            ing.delete()
            return JsonResponse({"ok": True, "name": name, "deleted": deleted, "remaining": 0, "deleted_all": True})

        # ลบบางส่วน
        ing.quantity = max(0, ing.quantity - amount)
        ing.save()
        return JsonResponse({"ok": True, "name": name, "deleted": int(amount), "remaining": ing.quantity, "deleted_all": False})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    
# ----- Recipe Suggest -----
import os, re, requests
from django.views.decorators.http import require_GET
from django.utils.timezone import now
from django.db.models import F
from django.http import JsonResponse
from .models import Ingredient

# ทำให้เปรียบเทียบชื่อแม่นขึ้น (ตัดเว้นวรรค/สัญลักษณ์/ตัวพิมพ์)
THAI_DIGITS = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')
def norm(s: str) -> str:
    if not s: return ''
    s = s.strip().lower().translate(THAI_DIGITS)
    s = re.sub(r'[^\wก-๙ ]+', ' ', s)  # เก็บอักษรไทย/อังกฤษ/ตัวเลขและเว้นวรรค
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# แม็พชื่อวัตถุดิบให้เป็นชื่อกลาง (ตัวอย่างเบื้องต้น ปรับเพิ่มได้)
CANON = {
    'basil': 'ใบกะเพรา',
    'holy basil': 'ใบกะเพรา',
    'thai basil': 'ใบกะเพรา',
    'basil leaves': 'ใบกะเพรา',
    'chili': 'พริก',
    'chilies': 'พริก',
    'red chili': 'พริก',
    'garlic': 'กระเทียม',
    'fish sauce': 'น้ำปลา',
    'soy sauce': 'ซีอิ๊ว',
    'oyster sauce': 'ซอสหอยนางรม',
    'sugar': 'น้ำตาล',
    'pork': 'หมู',
    'chicken': 'ไก่',
    'egg': 'ไข่ไก่',
    'eggs': 'ไข่ไก่',
    'rice': 'ข้าว',
    'oil': 'น้ำมันพืช',
    'ไก่': 'ไก่',
    'หมู': 'หมู',
    'เนื้อหมู': 'หมู',
    'ใบกะเพรา': 'ใบกะเพรา',
    'กะเพรา': 'ใบกะเพรา',
    'พริก': 'พริก',
    'กระเทียม': 'กระเทียม',
    'ซอสหอยนางรม': 'ซอสหอยนางรม',
    'ซีอิ๊ว': 'ซีอิ๊ว',
    'น้ำปลา': 'น้ำปลา',
    'น้ำตาล': 'น้ำตาล',
    'ไข่ไก่': 'ไข่ไก่',
    'ข้าว': 'ข้าว',
    'น้ำมัน': 'น้ำมันพืช',
    'น้ำมันพืช': 'น้ำมันพืช',
}

def canon_name(s: str) -> str:
    s2 = norm(s)
    # ตรงก่อน
    if s2 in CANON: return CANON[s2]
    # ลองแมตช์แบบ contains เบื้องต้น
    for k, v in CANON.items():
        if k in s2: return v
    return s.strip()

def fetch_ingredients_from_spoonacular(q: str):
    # ใช้ API Key จาก environment หรือจากตัวแปร
    key = os.environ.get('SPOONACULAR_API_KEY') or "4e8cc3a8b81e4022828e53a7ad94bc9d"
    
    # ถ้าไม่มี key หรือเป็น placeholder ให้ข้ามไปใช้ fallback
    if not key or key == "YOUR_SPOONACULAR_KEY":
        return None
        
    try:
        r = requests.get(
            "https://api.spoonacular.com/recipes/complexSearch",
            params={
                "query": q, "number": 1,
                "addRecipeInformation": "true",
                "fillIngredients": "true",
                "apiKey": key
            }, timeout=10
        )
        
        # ถ้า API ส่ง error 401 (unauthorized) ให้ข้ามไปใช้ fallback
        if r.status_code == 401:
            return None
            
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        if not results: return None
        ing = [i.get("name", "") for i in results[0].get("extendedIngredients", [])]
        title = results[0].get("title", q)
        return {"title": title, "ingredients": [i for i in ing if i]}
    except Exception:
        return None  # ใช้ fallback แทน

def fetch_ingredients_from_mealdb(q: str):
    try:
        r = requests.get("https://www.themealdb.com/api/json/v1/1/search.php", params={"s": q}, timeout=10)
        r.raise_for_status()
        data = r.json()
        meals = data.get("meals")
        if not meals: return None
        m = meals[0]
        ings = []
        for i in range(1, 21):
            val = m.get(f"strIngredient{i}") or ""
            val = val.strip()
            if val: ings.append(val)
        title = m.get("strMeal", q)
        return {"title": title, "ingredients": ings}
    except Exception:
        return None

# fallback ตัวอย่างเมนูไทยยอดฮิต
FALLBACK_RECIPES = {
    "ผัดกะเพรา": ["ใบกะเพรา", "พริก", "กระเทียม", "หมู", "น้ำปลา", "ซีอิ๊ว", "ซอสหอยนางรม", "น้ำตาล", "น้ำมันพืช", "ข้าว", "ไข่ไก่"],
    "ผัดกระเพรา": ["ใบกะเพรา", "พริก", "กระเทียม", "หมู", "น้ำปลา", "ซีอิ๊ว", "ซอสหอยนางรม", "น้ำตาล", "น้ำมันพืช", "ข้าว", "ไข่ไก่"],
    "ข้าวผัด": ["ข้าว", "ไข่ไก่", "หัวหอม", "กระเทียม", "หมู", "น้ำมันพืช", "ซีอิ๊ว"],
    "ไข่เจียว": ["ไข่ไก่", "น้ำมันพืช", "หัวหอม"],
    "ต้มยำ": ["กุ้ง", "ข่า", "ตะไคร้", "พริก", "มะนาว", "น้ำปลา", "น้ำตาล"],
    "ต้มยำกุ้ง": ["กุ้ง", "ข่า", "ตะไคร้", "พริก", "มะนาว", "น้ำปลา", "น้ำตาล"],
    "ส้มตำ": ["มะละกอ", "มะเขือเทศ", "ถั่วฝักยาว", "พริก", "กระเทียม", "มะนาว", "น้ำปลา", "น้ำตาล"],
    "แกงเขียวหวาน": ["พริกแกงเขียวหวาน", "กะทิ", "ไก่", "มะเขือ", "พริก", "ใบโหระพา"],
    "ผัดไทย": ["เส้นก๋วยเตี๋ยว", "กุ้ง", "ไข่ไก่", "ถั่วงอก", "กระเทียม", "น้ำปลา", "น้ำตาล", "ถั่วลิสง"],
    "ผัดซีอิ๊ว": ["เส้นก๋วยเตี๋ยว", "หมู", "คะน้า", "ซีอิ๊ว", "กระเทียม", "น้ำมันพืช"],
    "ข้าวเหนียวมะม่วง": ["ข้าวเหนียว", "มะม่วง", "กะทิ", "น้ำตาล", "เกลือ"],
    "ไก่ทอด": ["ไก่", "แป้ง", "กระเทียม", "น้ำมันพืช", "เกลือ", "พริกไทย"],
    "ซุป": ["มะเขือเทศ", "หัวหอม", "กระเทียม", "เกลือ", "น้ำ"],
    "ซุปมะเขือเทศ": ["มะเขือเทศ", "หัวหอม", "กระเทียม", "เกลือ", "น้ำ"],
}

def fetch_recipe_any(q: str):
    # 1) Spoonacular (ต้องมีคีย์)
    data = fetch_ingredients_from_spoonacular(q)
    if data: return data
    # 2) TheMealDB (เปิดได้ ไม่ต้องคีย์)
    data = fetch_ingredients_from_mealdb(q)
    if data: return data
    # 3) Fallback (กรณี dev/offline)
    qn = norm(q)
    for k, ings in FALLBACK_RECIPES.items():
        if norm(k) in qn or qn in norm(k):
            return {"title": k, "ingredients": ings}
    # ถ้าไม่เจอเลย
    return {"title": q, "ingredients": []}

def compare_with_inventory(recipe_ings, inv_names):
    # ทำเป็นชื่อ canon แล้ว set เทียบ
    recipe_canon = [canon_name(x) for x in recipe_ings]
    inv_canon = {canon_name(x) for x in inv_names}

    have, missing = [], []
    for item in recipe_canon:
        (have if item in inv_canon else missing).append(item)

    # เอา Duplicate ออกแบบคงลำดับ
    def dedup(seq):
        seen = set(); out=[]
        for x in seq:
            if x not in seen:
                out.append(x); seen.add(x)
        return out
    return dedup(have), dedup(missing)

def suggest(request):
    # แสดงหน้าเปล่าสำหรับค้น/พูด
    return render(request, "suggest.html")

def _norm(s: str) -> str:
    # ตัดเว้นวรรคและทำตัวพิมพ์เล็ก (รองรับไทย)
    return re.sub(r"\s+", "", (s or "").strip().lower())

@require_GET
def api_recipe_suggest(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"ok": False, "error": "กรุณาใส่ชื่อเมนู"}, status=400)

    # โหลดคลังเมนูจากไฟล์ local
    base_dir = os.path.dirname(__file__)
    with open(os.path.join(base_dir, "thai_recipes.json"), "r", encoding="utf-8") as f:
        recipes = json.load(f)

    qn = _norm(q)

    # 1) ตรงชื่อเป๊ะ
    match = next((r for r in recipes if _norm(r.get("title")) == qn), None)
    # 2) ไม่เจอลองแบบ contains
    if not match:
        cand = [r for r in recipes if qn in _norm(r.get("title"))]
        match = cand[0] if cand else None

    # ❌ ถ้ายังไม่เจอเลย → บอกไม่พบ (ไม่ fallback)
    if not match:
        return JsonResponse({"ok": False, "error": "ยังไม่มีรายละเอียดเมนู"}, status=404)

    # คำนวณ have / missing จากวัตถุดิบในระบบ
    ing_names = list(Ingredient.objects.values_list("name", flat=True))
    have_set = set(x.strip().lower() for x in ing_names)

    all_ings = match.get("ingredients", []) or []
    have = [x for x in all_ings if x.strip().lower() in have_set]
    missing = [x for x in all_ings if x.strip().lower() not in have_set]

    return JsonResponse({
        "ok": True,
        "dish": match.get("title") or q,
        "ingredients": all_ings,
        "have": have,
        "missing": missing,
    })
@require_POST
def decrement_ingredient(request, ingredient_id):
    ing = get_object_or_404(Ingredient, id=ingredient_id)
    if ing.quantity > 1:
        ing.quantity -= 1
        ing.save()
    else:
        ing.delete()  # ถ้าเหลือ 1 แล้วกด - ให้ลบรายการ
    return redirect('index')

@require_POST
def increment_ingredient(request, ingredient_id):
    ing = get_object_or_404(Ingredient, id=ingredient_id)
    ing.quantity += 1
    ing.save()
    return redirect('index')

with open(os.path.join(settings.BASE_DIR, "index", "thai_alias.json"), encoding="utf-8") as f:
    ingredient_map = json.load(f)

def recipes_from_spoonacular(request, ing_name):
    eng_name = ingredient_map.get(ing_name, ing_name)

    API_KEY = "4e8cc3a8b81e4022828e53a7ad94bc9d"  # <<< เก็บตรงนี้ ปลอดภัยกว่า

    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "ingredients": eng_name,
        "number": 5,
        "apiKey": API_KEY,
        "cuisine": "thai"
    }
    r = requests.get(url, params=params)
    return JsonResponse(r.json(), safe=False)





# โหลด mapping ไทย → อังกฤษ
with open(os.path.join(settings.BASE_DIR, "index", "thai_alias.json"), encoding="utf-8") as f:
    ingredient_map = json.load(f)

def recipes_from_spoonacular(request, ing_name):
    # แปลงไทย → อังกฤษ (ถ้าไม่มีใน map ใช้ชื่อเดิม)
    eng_name = ingredient_map.get(ing_name, ing_name)

    API_KEY = "4e8cc3a8b81e4022828e53a7ad94bc9d"

    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "ingredients": eng_name,
        "number": 10,
        "apiKey": API_KEY
    }
    r = requests.get(url, params=params)
    return JsonResponse(r.json(), safe=False)

with open(os.path.join(settings.BASE_DIR, "index", "thai_recipes.json"), encoding="utf-8") as f:
    THAI_RECIPES = json.load(f)

def local_thai_recipes(request, ing_name):
    results = []
    for recipe in THAI_RECIPES:
        if any(ing_name in i for i in recipe["ingredients"]):
            results.append(recipe)
    return JsonResponse(results, safe=False)



# ---------- utils ----------
def nrm(s: str) -> str:
    # normalize: ตัดช่องว่าง-แปลงเป็น lower ภาษาไทย/อังกฤษ
    return (s or "").strip().lower().replace(" ", "")

def th_lower(s): return (s or "").strip().lower()

def compare_with_inventory(all_ingredients, inventory_names):
    inv_norm = [th_lower(x) for x in inventory_names]
    have, missing = [], []
    for raw in all_ingredients:
        item = th_lower(raw)
        hit = any(item == x or item in x or x in item for x in inv_norm)
        (have if hit else missing).append(raw)
    # dedup
    def dedup_keep_order(arr):
        seen = set(); out = []
        for x in arr:
            if x not in seen:
                seen.add(x); out.append(x)
        return out
    return dedup_keep_order(have), dedup_keep_order(missing)

# ---------- เดาคำค้นไทย -> อังกฤษ (ขยายเองได้) ----------
THAI_RE = re.compile(r"[\u0E00-\u0E7F]")
QUERY_HINT = {
    "ผัดกะเพรา": "pad kra pao",
    "กะเพรา": "pad kra pao",
    "ต้มยำ": "tom yum",
    "ผัดไทย": "pad thai",
    "แกงเขียวหวาน": "green curry",
    "มัสมั่น": "massaman curry",
    "พะแนง": "panang curry",
    "แกงส้ม": "gaeng som",
    "แกงจืด": "thai clear soup",
    "ผัดซีอิ๊ว": "pad see ew",
    "ราดหน้า": "rad na",
    "คั่วกลิ้ง": "kua kling",
    "ยำวุ้นเส้น": "yum woon sen",
    "ไก่ผัดเม็ดมะม่วง": "chicken cashew",
    "ข้าวผัด": "thai fried rice"
}
def guess_query(q: str) -> str:
    s = (q or "").strip().lower()
    if not s: return s
    if THAI_RE.search(s):
        for k, v in QUERY_HINT.items():
            if k in s: return v
    return s

# ---------- Spoonacular ----------
def _spoonacular_complex_search(query: str, api_key: str, with_cuisine: bool):
    params = {
        "query": query,
        "number": 1,
        "addRecipeInformation": "true",
        "fillIngredients": "true",
        "apiKey": api_key,
    }
    if with_cuisine:
        params["cuisine"] = "thai"
    r = requests.get("https://api.spoonacular.com/recipes/complexSearch",
                     params=params, timeout=12)
    return r

def fetch_from_spoonacular_by_dish(q: str):
    api_key = getattr(settings, "SPOONACULAR_API_KEY", "")
    if not api_key:
        return None  # ไม่มีคีย์ -> ให้ fallback

    try:
        # รอบ 1: กรอง cuisine=thai
        r = _spoonacular_complex_search(q, api_key, with_cuisine=True)
        if r.status_code in (401, 402):  # key ผิด/โควต้าหมด
            return None
        if not r.ok:
            # ลองรอบ 2 แบบไม่กรอง cuisine
            r = _spoonacular_complex_search(q, api_key, with_cuisine=False)
        data = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        results = (data or {}).get("results") or []
        if not results:
            # ลองรอบ 2 ถ้ายังไม่ได้ลอง
            if "cuisine" in r.request.url:
                r2 = _spoonacular_complex_search(q, api_key, with_cuisine=False)
                data2 = r2.json() if r2.ok else {}
                results = (data2 or {}).get("results") or []
        if not results:
            return None

        m = results[0]
        title = m.get("title") or q
        ings = []
        for it in m.get("extendedIngredients", []) or []:
            name = it.get("name")
            if name: ings.append(name)
        return {"title": title, "ingredients": ings}

    except Exception:
        return None

# ---------- Fallback: thai_recipes.json ----------
def fetch_from_local_json(q: str):
    # ปรับพาธให้ชี้ไปที่แอป index/ (แก้ตามโครงสร้างโปรเจกต์คุณ)
    path = os.path.join(settings.BASE_DIR, "index", "thai_recipes.json")
    if not os.path.exists(path):
        # เผื่อบางคนวางไว้ที่ root
        alt = os.path.join(settings.BASE_DIR, "thai_recipes.json")
        path = alt if os.path.exists(alt) else path

    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            recipes = json.load(f)
        if not isinstance(recipes, list):
            return None

        qn = nrm(q)
        best = None

        for rec in recipes:
            title = rec.get("title") or rec.get("name") or ""
            ings  = rec.get("ingredients") or []
            tn = nrm(title)
            # แมตช์แบบยืดหยุ่น: contains หลัง normalize
            if qn and qn in tn:
                return {"title": title, "ingredients": ings}
            # เก็บอันแรกไว้เป็นตัวเลือกท้ายสุด
            if best is None:
                best = {"title": title, "ingredients": ings}

        return best  # ถ้าไม่เจอคำใกล้เคียงเลย คืนรายการแรก

    except Exception:
        return None

# ---------- API สำหรับ suggest.html ----------
@require_GET
def api_recipe_suggest(request):
    raw_q = (request.GET.get("q") or "").strip()
    if not raw_q:
        return JsonResponse({"ok": False, "error": "missing q"}, status=400)

    query = guess_query(raw_q)  # เดาคีย์อังกฤษถ้าเป็นไทย
    recipe = fetch_from_spoonacular_by_dish(query)

    # ถ้า Spoonacular ใช้ไม่ได้/ไม่เจอ -> ลอง local JSON
    if not recipe:
        recipe = fetch_from_local_json(raw_q)  # ใช้คีย์ไทยหาใน local จะยืดหยุ่นกว่า

    if not recipe:
        return JsonResponse({"ok": False, "error": "ไม่พบเมนู"}, status=404)

    inv_names = list(Ingredient.objects.values_list("name", flat=True))
    have, missing = compare_with_inventory(recipe["ingredients"], inv_names)

    return JsonResponse({
        "ok": True,
        "dish": recipe["title"],
        "ingredients": recipe["ingredients"],
        "have": have,
        "missing": missing,
    })

def local_recipes(request):
    path = os.path.join(settings.BASE_DIR, "index", "thai_recipes.json")
    if not os.path.exists(path):
        return JsonResponse({"ok": False, "error": f"file not found: {path}"}, status=404)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return JsonResponse({"ok": False, "error": "thai_recipes.json must be an array"}, status=500)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
    

def _to_lower_th(s): 
    return (s or "").strip().lower()

@require_POST
def voice_delete_ingredient(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    name = _to_lower_th(data.get("name"))
    amount = data.get("amount")

    if not name:
        return JsonResponse({"ok": False, "error": "missing name"}, status=400)

    # หาวัตถุดิบตามชื่อ (กรณีมีช่องว่าง/ตัวพิมพ์)
    try:
        ing = Ingredient.objects.get(name__iexact=name)
    except Ingredient.DoesNotExist:
        # เผื่อพิมพ์สั้น ๆ ตรงต้นหรือมีเว้นวรรค
        ing = Ingredient.objects.filter(
            Q(name__iexact=name) | Q(name__icontains=name)
        ).order_by("id").first()

    if not ing:
        return JsonResponse({"ok": False, "error": f"ไม่พบบันทึกชื่อ: {name}"} , status=404)

    # จัดการลบ
    if str(amount).lower() == "all":
        deleted = ing.quantity
        ing.delete()
        return JsonResponse({
            "ok": True,
            "deleted_all": True,
            "deleted": deleted,
            "remaining": 0
        })

    # จำนวนเป็นตัวเลข
    try:
        amt = int(amount)
    except Exception:
        amt = 1

    amt = max(1, amt)
    deleted = min(amt, ing.quantity)
    ing.quantity = ing.quantity - deleted
    if ing.quantity <= 0:
        ing.delete()
        remaining = 0
    else:
        ing.save()
        remaining = ing.quantity

    return JsonResponse({
        "ok": True,
        "deleted_all": False,
        "deleted": deleted,
        "remaining": remaining
    })

def map_th_en(name: str) -> str:
    n = (name or "").strip().lower()
    return TH_EN.get(n, n)  # ถ้าไม่มี mapping ก็ส่งชื่อเดิมไป

def _today():
    return datetime.date.today()

def ingredient_days_remaining(expiry_date):
    if not expiry_date:
        return 9999
    return (expiry_date - _today()).days

def call_spoonacular_by_ingredients(ing_names_en, number=12):
    """เรียก Spoonacular แบบ findByIngredients จากรายชื่อวัตถุดิบอังกฤษ"""
    key = getattr(settings, "SPOONACULAR_API_KEY", None) or os.environ.get("SPOONACULAR_API_KEY")
    if not key:
        raise RuntimeError("missing SPOONACULAR_API_KEY")

    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "ingredients": ",".join(ing_names_en),
        "number": number,
        "ranking": 2,          # เน้นใช้วัตถุดิบให้มาก
        "ignorePantry": True,
        "apiKey": key,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def load_local_recipes():
    """โหลด fallback json: index/thai_recipes.json"""
    path = os.path.join(settings.BASE_DIR, "index", "thai_recipes.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    return data

def score_local(recipes, ing_names_th):
    """ให้คะแนนสูตร local ตาม overlap ของวัตถุดิบที่มี (ไทย)"""
    scored = []
    have_set = set([ (n or "").lower() for n in ing_names_th ])
    for r in recipes:
        ings = [ (x or "").lower() for x in (r.get("ingredients") or []) ]
        used = [x for x in ings if x in have_set]
        miss = [x for x in ings if x not in have_set]
        score = len(used) - 0.3*len(miss)
        scored.append({
            "title": r.get("title") or r.get("name") or "เมนู",
            "image": r.get("image"),
            "used": used,
            "missing": miss,
            "score": score,
        })
    # เรียงจากคะแนนมากไปน้อย
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

def api_daily_recs(request):
    """
    คืน 6 เมนูแนะนำประจำวันตามวัตถุดิบที่มี + ใกล้หมดอายุ
    รูปแบบผลลัพธ์: [{"title":..., "image":..., "used":[...], "missing":[...]}, ...]
    """
    # 1) ดึงวัตถุดิบทั้งหมด เรียงใกล้หมดก่อน
    ings = list(Ingredient.objects.all())
    if not ings:
        return JsonResponse([], safe=False)

    # คำนวณ days_remaining (ถ้าโมเดลคุณมีฟิลด์นี้อยู่แล้วจะง่าย)
    ings_sorted = sorted(ings, key=lambda x: ingredient_days_remaining(x.expiry_date))

    # เลือก top-k เป็นชุด seed (เช่น 5-8 รายการ)
    seed = ings_sorted[:8]

    ing_names_th = [i.name for i in seed if i.quantity and i.quantity > 0]
    ing_names_en = [map_th_en(n) for n in ing_names_th]

    # 2) ลอง Spoonacular ก่อน (findByIngredients)
    results = []
    try:
        sp = call_spoonacular_by_ingredients(ing_names_en, number=12)
        # sp แต่ละตัวอย่างจะมี fields: id, title, image, usedIngredients, missedIngredients
        for rec in sp:
            used = [ u.get("name") for u in rec.get("usedIngredients", []) ]
            miss = [ m.get("name") for m in rec.get("missedIngredients", []) ]
            results.append({
                "title": rec.get("title"),
                "image": rec.get("image"),
                "used": used,
                "missing": miss
            })
    except Exception:
        # 3) Fallback: local json
        local = load_local_recipes()
        scored = score_local(local, ing_names_th)
        for it in scored:
            results.append({
                "title": it["title"],
                "image": it.get("image"),
                "used": it.get("used", []),
                "missing": it.get("missing", [])
            })

    # ตัดให้เหลือแค่ 6
    return JsonResponse(results[:6], safe=False)

def _today():
    # คืนค่าวันปัจจุบันตาม timezone ของโปรเจกต์
    return timezone.localdate()

def ingredient_days_remaining(expiry_date):
    if not expiry_date:
        return 999
    # ถ้าเป็น string เช่น "2025-10-06" แปลงเป็น date ก่อน
    if isinstance(expiry_date, str):
        expiry_date = _date.fromisoformat(expiry_date)
    return (expiry_date - _today()).days