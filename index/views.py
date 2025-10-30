from django.shortcuts import render, redirect, get_object_or_404
from .models import Ingredient, IngredientImage
from datetime import date , timedelta , datetime 
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.views.decorators.http import require_POST
import json 
from django.conf import settings
from django.db.models import Q
from datetime import date as _date
from django.utils import timezone
from django.db import transaction
from pathlib import Path



with open("index/thai_alias.json", "r", encoding="utf-8") as f:
    TH_EN = json.load(f)

# --- helpers: normalize ---
def _nrm(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "")

from collections import defaultdict

EN_TH = defaultdict(set)   
if isinstance(TH_EN, dict):
    for th, en in TH_EN.items():
        th_n = _nrm(th)
        if isinstance(en, str):
            EN_TH[_nrm(en)].add(th_n)
        elif isinstance(en, list):
            for e in en:
                EN_TH[_nrm(e)].add(th_n)

EXTRA_EN_TH = {
    "egg": {"ไข่"},
    "eggs": {"ไข่"},
    "pork": {"หมู"},
    "chicken": {"ไก่"},
    "tomato": {"มะเขือเทศ"},
    "tomatoes": {"มะเขือเทศ"},
    "chili": {"พริก"},
    "chilies": {"พริก"},
    "chilly": {"พริก"},
    "chillys": {"พริก"},
    "garlic": {"กระเทียม"},
    "fish sauce": {"น้ำปลา"},
    # --- proteins & meats ---
    "chicken": {"ไก่"},
    "pork": {"หมู"},
    "beef": {"เนื้อวัว"},
    "duck": {"เป็ด"},
    "turkey": {"ไก่งวง"},
    "lamb": {"เนื้อแกะ"},
    "bacon": {"เบคอน"},
    "ham": {"แฮม"},
    "sausage": {"ไส้กรอก"},
    "meatball": {"ลูกชิ้น"},
    "minced pork": {"หมูสับ", "หมูบด"},
    "minced chicken": {"ไก่สับ", "ไก่บด"},
    "minced beef": {"เนื้อสับ", "เนื้อบด"},
    "ground pork": {"หมูบด", "หมูสับ"},
    "ground chicken": {"ไก่บด", "ไก่สับ"},
    "ground beef": {"เนื้อบด", "เนื้อสับ"},

    # --- seafood ---
    "shrimp": {"กุ้ง"},
    "prawn": {"กุ้ง"},
    "fish": {"ปลา"},
    "salmon": {"ปลาแซลมอน"},
    "tuna": {"ปลาทูน่า"},
    "squid": {"ปลาหมึก"},
    "octopus": {"ปลาหมึกยักษ์", "หมึกยักษ์"},
    "crab": {"ปู"},
    "mussel": {"หอยแมลงภู่"},
    "clam": {"หอยลาย"},
    "scallop": {"หอยเชลล์"},
    "oyster": {"หอยนางรม"},

    # --- vegetables common ---
    "tomato": {"มะเขือเทศ"},
    "tomatoes": {"มะเขือเทศ"},
    "potato": {"มันฝรั่ง"},
    "potatoes": {"มันฝรั่ง"},
    "sweet potato": {"มันเทศ"},
    "onion": {"หัวหอม", "หอมใหญ่"},
    "onions": {"หัวหอม", "หอมใหญ่"},
    "shallot": {"หอมแดง"},
    "garlic": {"กระเทียม"},
    "ginger": {"ขิง"},
    "galangal": {"ข่า"},
    "lemongrass": {"ตะไคร้"},
    "kaffir lime leaves": {"ใบมะกรูด"},
    "lime": {"มะนาว"},
    "lemon": {"เลมอน"},
    "chili": {"พริก"},
    "chilies": {"พริก"},
    "bird's eye chili": {"พริกขี้หนู"},
    "bell pepper": {"พริกหยวก", "พริกหวาน"},
    "capsicum": {"พริกหวาน"},
    "cucumber": {"แตงกวา"},
    "carrot": {"แครอท"},
    "cabbage": {"กะหล่ำปลี"},
    "chinese cabbage": {"ผักกาดขาว"},
    "napa cabbage": {"ผักกาดขาว"},
    "kale": {"คะน้า"},
    "broccoli": {"บรอกโคลี"},
    "cauliflower": {"กะหล่ำดอก"},
    "spinach": {"ผักโขม"},
    "morning glory": {"ผัดผักบุ้ง", "ผักบุ้ง"},
    "water spinach": {"ผักบุ้ง"},
    "pumpkin": {"ฟักทอง"},
    "eggplant": {"มะเขือยาว"},
    "thai eggplant": {"มะเขือเปราะ"},
    "pea eggplant": {"มะเขือพวง"},
    "mushroom": {"เห็ด"},
    "straw mushroom": {"เห็ดฟาง"},
    "oyster mushroom": {"เห็ดนางรม"},
    "shiitake": {"เห็ดหอม"},
    "enoki": {"เห็ดเข็มทอง"},
    "corn": {"ข้าวโพด"},
    "baby corn": {"ข้าวโพดอ่อน"},
    "asparagus": {"หน่อไม้ฝรั่ง"},
    "bamboo shoot": {"หน่อไม้"},
    "bean sprout": {"ถั่วงอก"},
    "yardlong bean": {"ถั่วฝักยาว"},
    "long bean": {"ถั่วฝักยาว"},
    "green bean": {"ถั่วแขก"},
    "lettuce": {"ผักกาดหอม"},
    "celery": {"ขึ้นฉ่าย"},
    "spring onion": {"ต้นหอม"},
    "green onion": {"ต้นหอม"},
    "scallion": {"ต้นหอม"},
    "coriander": {"ผักชี"},
    "cilantro": {"ผักชี"},
    "parsley": {"พาสลีย์", "ผักชีฝรั่ง"},
    "basil": {"โหระพา"},
    "thai basil": {"โหระพา"},
    "sweet basil": {"โหระพา"},
    "holy basil": {"ใบกะเพรา"},
    "mint": {"สะระแหน่"},
    "dill": {"ผักชีลาว"},
    "pandan": {"ใบเตย"},

    # --- grains, noodles & carbs ---
    "rice": {"ข้าว"},
    "jasmine rice": {"ข้าวหอมมะลิ"},
    "glutinous rice": {"ข้าวเหนียว"},
    "sticky rice": {"ข้าวเหนียว"},
    "noodles": {"เส้นก๋วยเตี๋ยว", "บะหมี่", "เส้น"},
    "rice noodles": {"เส้นก๋วยเตี๋ยว", "เส้นจันท์"},
    "glass noodles": {"วุ้นเส้น"},
    "vermicelli": {"วุ้นเส้น"},
    "egg noodles": {"บะหมี่ไข่"},
    "instant noodles": {"บะหมี่กึ่งสำเร็จรูป"},
    "rice paper": {"แผ่นแป้งเวียดนาม"},
    "bread": {"ขนมปัง"},
    "flour": {"แป้งสาลี"},
    "wheat flour": {"แป้งสาลี"},
    "rice flour": {"แป้งข้าวเจ้า"},
    "tapioca flour": {"แป้งมัน"},
    "cornstarch": {"แป้งข้าวโพด"},
    "corn starch": {"แป้งข้าวโพด"},

    # --- dairy & fats ---
    "milk": {"นม", "นมโค"},
    "yogurt": {"โยเกิร์ต"},
    "butter": {"เนย"},
    "cheese": {"ชีส"},
    "cream": {"ครีม"},
    "whipping cream": {"วิปปิ้งครีม"},
    "mayonnaise": {"มายองเนส"},
    "coconut milk": {"กะทิ"},
    "coconut cream": {"หัวกะทิ"},
    "oil": {"น้ำมันพืช", "น้ำมัน"},
    "vegetable oil": {"น้ำมันพืช"},
    "olive oil": {"น้ำมันมะกอก"},
    "sesame oil": {"น้ำมันงา"},
    "peanut oil": {"น้ำมันถั่วลิสง"},
    "coconut oil": {"น้ำมันมะพร้าว"},

    # --- sauces & condiments ---
    "fish sauce": {"น้ำปลา"},
    "soy sauce": {"ซีอิ๊ว"},
    "light soy sauce": {"ซีอิ๊วขาว"},
    "dark soy sauce": {"ซีอิ๊วดำ"},
    "oyster sauce": {"ซอสหอยนางรม"},
    "hoisin sauce": {"ซอสฮอยซิน"},
    "sriracha": {"ซอสศรีราชา"},
    "chili paste": {"พริกเผา", "น้ำพริกเผา"},
    "chili oil": {"น้ำมันพริก"},
    "chili flakes": {"พริกป่น"},
    "curry paste": {"พริกแกง"},
    "red curry paste": {"พริกแกงเผ็ด"},
    "green curry paste": {"พริกแกงเขียวหวาน"},
    "panang curry paste": {"พริกแกงพะแนง"},
    "panaeng curry paste": {"พริกแกงพะแนง"},
    "massaman curry paste": {"พริกแกงมัสมั่น"},
    "tom yum paste": {"พริกแกงต้มยำ"},
    "tamarind": {"มะขาม"},
    "tamarind paste": {"น้ำมะขามเปียก"},
    "vinegar": {"น้ำส้มสายชู"},
    "rice vinegar": {"น้ำส้มสายชูญี่ปุ่น"},
    "white vinegar": {"น้ำส้มสายชูกลั่น"},
    "apple cider vinegar": {"น้ำส้มแอปเปิลไซเดอร์"},
    "sugar": {"น้ำตาล"},
    "palm sugar": {"น้ำตาลปี๊บ", "น้ำตาลมะพร้าว"},
    "brown sugar": {"น้ำตาลทรายแดง"},
    "white sugar": {"น้ำตาลทรายขาว"},
    "salt": {"เกลือ"},
    "sea salt": {"เกลือทะเล"},
    "black pepper": {"พริกไทยดำ"},
    "white pepper": {"พริกไทยขาว"},
    "peppercorn": {"เม็ดพริกไทย"},
    "shrimp paste": {"กะปิ"},

    # --- spices & aromatics ---
    "turmeric": {"ขมิ้น"},
    "cumin": {"ยี่หร่า"},
    "coriander seed": {"เมล็ดผักชี"},
    "fennel seed": {"เมล็ดยี่หร่าเทศ"},
    "star anise": {"โป๊ยกั๊ก"},
    "cinnamon": {"อบเชย"},
    "cardamom": {"กระวาน"},
    "clove": {"กานพลู"},
    "bay leaf": {"ใบกระวาน"},
    "white sesame": {"งาขาว"},
    "black sesame": {"งาดำ"},

    # --- nuts, beans & tofu ---
    "peanut": {"ถั่วลิสง"},
    "cashew": {"เม็ดมะม่วงหิมพานต์"},
    "almond": {"อัลมอนด์"},
    "sesame": {"งา"},
    "sunflower seed": {"เมล็ดทานตะวัน"},
    "tofu": {"เต้าหู้"},
    "firm tofu": {"เต้าหู้แข็ง"},
    "soft tofu": {"เต้าหู้อ่อน"},
    "soybean": {"ถั่วเหลือง"},
    "mung bean": {"ถั่วเขียว"},
    "red bean": {"ถั่วแดง"},
    "black bean": {"ถั่วดำ"},
    "chickpea": {"ถั่วชิกพี", "ถั่วลูกไก่"},
    "lentil": {"ถั่วเลนทิล"},


    
}
for k, vs in EXTRA_EN_TH.items():
    EN_TH[_nrm(k)].update({_nrm(v) for v in vs})

def _singularize_en(s: str) -> str:
    s = (s or "").lower()
    if s.endswith("ies"):  # berries -> berry
        return s[:-3] + "y"
    if s.endswith("es") and not s.endswith(("ses","xes","zes","ches","shes")):
        return s[:-2]
    if s.endswith("s") and not s.endswith("ss"):
        return s[:-1]
    return s

def local_keys_for(name: str):
    """
    รับชื่อวัตถุดิบ (อังกฤษ/ไทย) -> คืน set ของ 'คีย์ภาษาไทยแบบ normalize'
    ที่ใช้ค้นใน thai_recipes.json
    """
    keys = set()
    raw = (name or "").strip()
    n = _nrm(raw)
    keys.add(n)

    # ถ้าเป็นอังกฤษ: ลองแปลงพหูพจน์ -> เอกพจน์ แล้วแม็พ EN->TH
    sing = _nrm(_singularize_en(raw))
    if sing != n:
        keys.add(sing)

    # แม็พ EN->TH (เพิ่มคีย์ไทย)
    keys |= EN_TH.get(n, set())
    keys |= EN_TH.get(sing, set())

    return keys



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
        expiry_dt   = date.fromisoformat(expiry_s)

        # อัปโหลด/อัปเดตรูป (ถ้ามี)
        image_file = request.FILES.get("image_file")
        image_obj = None
        if image_file:
            img, _ = IngredientImage.objects.get_or_create(name=name)
            img.image = image_file
            img.save()
            image_obj = img

        # ✅ ไม่รวมรายการเดิม — สร้างใหม่ทุกครั้ง
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
    try:
        data = json.loads(request.body.decode('utf-8'))
        name = (data.get('name') or '').strip()
        quantity = int(data.get('quantity') or 1)
        prepared_s = data.get('prepared_date') or date.today().isoformat()
        expiry_s   = data.get('expiry_date')

        if not name:
            return HttpResponseBadRequest('Missing name')
        if not expiry_s:
            expiry_s = (date.fromisoformat(prepared_s) + timedelta(days=7)).isoformat()

        prepared_dt = date.fromisoformat(prepared_s)
        expiry_dt   = date.fromisoformat(expiry_s)

        # ✅ ไม่รวมรายการเดิม — สร้างใหม่ทุกครั้ง
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
    "ผัดกะเพรา": ["ใบกะเพรา", "พริก", "กระเทียม", "หมู", "น้ำปลา", "ซีอิ๊ว", "ซอสหอยนางรม", "น้ำตาล", "น้ำมันพืช", "ข้าว"],
    "ผัดกระเพรา": ["ใบกะเพรา", "พริก", "กระเทียม", "หมู", "น้ำปลา", "ซีอิ๊ว", "ซอสหอยนางรม", "น้ำตาล", "น้ำมันพืช", "ข้าว"],
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

    API_KEY = "4e8cc3a8b81e4022828e53a7ad94bc9d"  

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
        "number": 6,
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
@transaction.atomic
def voice_delete_ingredient(request):
    """
    JSON: {name, amount=number|"all", policy="oldest|newest|nearest_expiry|by_date", target_date?}
    ล็อกิก:
      - หา records ทั้งหมดของชื่อวัตถุดิบ (case-insensitive)
      - เลือก order ตาม policy
      - ลบ/หักจำนวนจากล็อตแรกตามลำดับ จนกว่าจะครบ amount หรือหมด
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    name = (data.get("name") or "").strip()
    amount = data.get("amount", "all")
    policy = (data.get("policy") or "oldest").strip().lower()
    target_date = data.get("target_date")  # ใช้เมื่อ policy = by_date

    if not name:
        return JsonResponse({"ok": False, "error": "missing name"}, status=400)

    # ยันให้ amount เป็น int หรือ "all"
    delete_all = False
    if isinstance(amount, str):
        if amount.strip().lower() in {"all", "ทั้งหมด"}:
            delete_all = True
        else:
            try:
                amount = int(amount)
            except Exception:
                return JsonResponse({"ok": False, "error": "amount must be int or 'all'"}, status=400)
    elif isinstance(amount, int):
        delete_all = (amount <= 0)
    else:
        return JsonResponse({"ok": False, "error": "invalid amount"}, status=400)

    from .models import Ingredient
    qs = Ingredient.objects.filter(name__iexact=name)

    if not qs.exists():
        return JsonResponse({"ok": False, "error": f"ไม่พบบันทึกชื่อ '{name}'"}, status=404)

    ordered = pick_queryset_for_policy(qs, policy, target_date)

    # รองรับทั้งกรณี list (nearest_expiry) และ queryset
    items = list(ordered) if not isinstance(ordered, list) else ordered

    total_deleted = 0
    lots_affected = []

    if delete_all:
        for it in items:
            total_deleted += it.quantity
            lots_affected.append({"id": it.id, "deleted": it.quantity})
            it.delete()
        return JsonResponse({
            "ok": True,
            "name": name,
            "deleted_all": True,
            "deleted": total_deleted,
            "lots": lots_affected
        })

    # ลบตามจำนวน amount ข้ามล็อตได้
    remain = int(amount)
    for it in items:
        if remain <= 0:
            break
        take = min(remain, it.quantity)
        if take >= it.quantity:
            lots_affected.append({"id": it.id, "deleted": it.quantity})
            total_deleted += it.quantity
            remain -= it.quantity
            it.delete()
        else:
            it.quantity -= take
            it.save(update_fields=["quantity"])
            lots_affected.append({"id": it.id, "deleted": take, "left": it.quantity})
            total_deleted += take
            remain -= take

    return JsonResponse({
        "ok": True,
        "name": name,
        "deleted_all": False,
        "requested": amount,
        "deleted": total_deleted,
        "remaining_to_delete": max(0, remain),
        "lots": lots_affected
    })


# คำนวณวันหมดอายุใน Python แล้วจัดเรียง/คัดกรองให้
def _safe_expiry(obj):
    """
    คืนวันหมดอายุจากค่าที่มี (field expiry_date ถ้ามี)
    ถ้าไม่มีให้คำนวณจาก prepared_date + shelf_life_days
    และกัน None ทุกจุด
    """
    pd = obj.prepared_date or date.today()
    sld = (obj.shelf_life_days or 0)
    # ถ้ามี field expiry_date ใช้ก่อน
    if getattr(obj, "expiry_date", None):
        return obj.expiry_date
    return pd + timedelta(days=sld)

def pick_queryset_for_policy(qs, policy, target_date=None):
    """
    รับ queryset ของ Ingredient แล้วคืนลำดับ/รายการตาม policy
    - newest        : created_at ใหม่สุดก่อน
    - oldest        : created_at เก่าสุดก่อน
    - nearest_expiry: หมดอายุใกล้สุดก่อน (คำนวณใน Python)
    - expired_only  : เฉพาะที่หมดอายุแล้ว (วันนี้ > expiry) เรียงจากหมดอายุก่อน
    - by_date       : เฉพาะล็อตที่หมดอายุ 'ตรงวัน' target_date (YYYY-MM-DD)
    คืนได้เป็น queryset (กรณี newest/oldest) หรือ list (กรณีอื่น)
    """
    p = (policy or "").lower()

    if p == "newest":
        return qs.order_by("-created_at")

    if p == "oldest":
        return qs.order_by("created_at")

    items = list(qs)  # ดึงมาเป็น list เพื่อคัดกรอง/จัดเรียงใน Python

    if p == "expired_only":
        today = timezone.localdate()
        items = [x for x in items if _safe_expiry(x) and _safe_expiry(x) < today]
        items.sort(key=lambda x: (_safe_expiry(x), x.created_at))
        return items

    if p == "by_date":
        try:
            tgt = date.fromisoformat((target_date or "").strip())
        except Exception:
            # ถ้าพาร์สไม่ผ่าน ให้ทำเหมือน nearest_expiry
            tgt = None
        if tgt:
            items = [x for x in items if _safe_expiry(x) == tgt]
        items.sort(key=lambda x: (_safe_expiry(x), x.created_at))
        return items

    # default -> nearest_expiry
    items.sort(key=lambda x: (_safe_expiry(x), x.created_at))
    return items




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


@require_GET
def api_daily_recs_local(request):
    """
    คืน 6 เมนูจาก thai_recipes.json โดย:
      - พิจารณาวัตถุดิบในสต็อก (ของจริงใน DB)
      - ให้ความสำคัญกับวัตถุดิบที่ใกล้หมดอายุก่อน (เหมือน api_daily_recs)
      - คำนวณ used / missing ให้เรียบร้อย
    รูปแบบผลลัพธ์: [{"title","image","used":[...],"missing":[...],"source":"local"}, ...]
    """
    # 1) ดึงวัตถุดิบทั้งหมด เรียงใกล้หมดก่อน
    ings = list(Ingredient.objects.all())
    if not ings:
        return JsonResponse([], safe=False)

    ings_sorted = sorted(ings, key=lambda x: ingredient_days_remaining(x.expiry_date))

    # เลือก top-k เป็นชุด seed เพื่อชี้นำเมนู (8 รายการแรก)
    seed = ings_sorted[:8]
    ing_names_th = [i.name for i in seed if (i.quantity or 0) > 0]

    # 2) โหลดสูตรจากไฟล์ local และให้คะแนนตามวัตถุดิบที่ “มี”
    local = load_local_recipes()  # list ของ recipe dict
    scored = score_local(local, ing_names_th)  # ใส่ score, used, missing

    # 3) สร้างผลลัพธ์ 6 รายการแรก
    out = []
    for it in scored[:3]:
        out.append({
            "title": it.get("title"),
            "image": it.get("image"),
            "used": it.get("used", []),
            "missing": it.get("missing", []),
            "source": "local",
        })
    return JsonResponse(out, safe=False)

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

@require_GET
def recipes_by_ingredient(request, ing_name):
    """
    GET /api/recipes/<ing_name>/?source=api|local&limit=10
    คืน: [{"title":..., "image":..., "used":[...], "missing":[...]}, ...]
    """
    source = (request.GET.get("source") or "api").lower()
    limit = int(request.GET.get("limit") or 10)

    # รายชื่อวัตถุดิบในสต็อค (ไว้คำนวณ used/missing)
    inv_names_th = list(Ingredient.objects.values_list("name", flat=True))

    results = []
    try:
        if source == "api":
            # เรียก Spoonacular ด้วย findByIngredients จาก “วัตถุดิบเดียว”
            ing_en = map_th_en(ing_name)
            sp = call_spoonacular_by_ingredients([ing_en], number=limit)
            for rec in sp:
                used = [u.get("name") for u in rec.get("usedIngredients", [])]
                miss = [m.get("name") for m in rec.get("missedIngredients", [])]
                results.append({
                    "title": rec.get("title"),
                    "image": rec.get("image"),
                    "used": used,
                    "missing": miss,
                    "source": "api",
                    "rid": rec.get("id"),
                })
        else:
            # --- Local: รองรับชื่ออังกฤษ → ไทย โดยใช้ local_keys_for ---
            local = load_local_recipes()  # list ของ recipe dict
            keys = local_keys_for(ing_name)  # คีย์ไทยแบบ normalize แล้ว
            inv_norm = [_nrm(n) for n in inv_names_th]

            filtered = []
            for r in local:
                ings_raw = r.get("ingredients") or []
                ings_norm = [_nrm(x) for x in ings_raw]

                # ติดถ้ามีคีย์ใด ๆ ปรากฏในส่วนผสม (เช็คแบบ contains สองทาง)
                hit = any(any(k in ing or ing in k for k in keys) for ing in ings_norm)
                if not hit:
                    continue

                used = [x for x in ings_raw if _nrm(x) in inv_norm]
                miss = [x for x in ings_raw if _nrm(x) not in inv_norm]

                filtered.append({
                    "title": r.get("title") or r.get("name") or "เมนู",
                    "image": r.get("image"),
                    "used": used,
                    "missing": miss,
                    "source": "local",
                })

            filtered.sort(key=lambda x: (len(x["used"]), -len(x["missing"])), reverse=True)
            results = filtered[:limit]

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse(results, safe=False)

@require_GET
def recipe_instructions(request):
    """
    GET /api/recipe_instructions/?source=api|local&rid=<id>&title=<title>
    - source=api: ใช้ rid (Spoonacular id)
    - source=local: ใช้ title ค้นใน thai_recipes.json และคืน steps/instructions ถ้ามี
    return: {"ok": True, "title": "...", "steps": ["...", "..."]}
    """
    source = (request.GET.get("source") or "api").lower()
    steps = []
    title = request.GET.get("title") or ""

    if source == "api":
        rid = request.GET.get("rid")
        api_key = getattr(settings, "SPOONACULAR_API_KEY", "") or os.environ.get("SPOONACULAR_API_KEY")
        if not (rid and api_key):
            return JsonResponse({"ok": False, "error": "missing rid or api key"}, status=400)

        try:
            r = requests.get(
                f"https://api.spoonacular.com/recipes/{rid}/analyzedInstructions",
                params={"apiKey": api_key},
                timeout=10
            )
            if r.status_code in (401, 402):
                return JsonResponse({"ok": False, "error": "Spoonacular key invalid or quota exceeded"}, status=502)

            r.raise_for_status()
            data = r.json() or []
            # โครงสร้างจะเป็น list ของ instruction sets -> แต่ละ set มี steps เป็นลิสต์
            for instr_set in data:
                for st in instr_set.get("steps", []):
                    txt = st.get("step")
                    if txt:
                        steps.append(txt.strip())

            if not steps:
                return JsonResponse({"ok": False, "error": "ไม่พบวิธีทำจาก API"}, status=404)

            return JsonResponse({"ok": True, "title": title, "steps": steps})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=500)

    # ----- LOCAL -----
    # หาใน thai_recipes.json ว่ามีฟิลด์ instructions/steps ไหม
    path = os.path.join(settings.BASE_DIR, "index", "thai_recipes.json")
    if not os.path.exists(path):
        return JsonResponse({"ok": False, "error": "local recipe file not found"}, status=404)

    try:
        with open(path, "r", encoding="utf-8") as f:
            arr = json.load(f)
        title_n = (title or "").strip().lower()
        rec = None
        for it in arr:
            t = (it.get("title") or it.get("name") or "").strip()
            if t.lower() == title_n:
                rec = it
                break
        if not rec:
            # ไม่เจอชื่อเป๊ะ ลอง contains
            for it in arr:
                t = (it.get("title") or it.get("name") or "").strip()
                if title_n and title_n in t.lower():
                    rec = it
                    break

        if not rec:
            return JsonResponse({"ok": False, "error": "ไม่พบเมนูใน local"}, status=404)

        # รองรับได้ทั้ง "instructions" (string/list) หรือ "steps" (list)
        if isinstance(rec.get("steps"), list):
            steps = [str(x).strip() for x in rec["steps"] if str(x).strip()]
        elif isinstance(rec.get("instructions"), list):
            steps = [str(x).strip() for x in rec["instructions"] if str(x).strip()]
        elif isinstance(rec.get("instructions"), str):
            # แยกบรรทัด
            steps = [x.strip() for x in rec["instructions"].split("\n") if x.strip()]

        if not steps:
            return JsonResponse({"ok": False, "error": "เมนูนี้ยังไม่มีวิธีทำใน local"}, status=404)

        return JsonResponse({"ok": True, "title": rec.get("title") or rec.get("name") or title, "steps": steps})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@require_POST
def adjust_ingredient(request, ingredient_id):
    """
    รับ POST JSON: {"delta": <int>}
    delta > 0 = เพิ่มจำนวน, delta < 0 = ลดจำนวน
    ถ้าจำนวนใหม่ <= 0 ให้ลบรายการ
    คืน: {"ok": True, "new_quantity": int, "deleted": bool}
    """
    try:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            # fallback เป็น form-encoded
            data = request.POST
        delta = int(data.get("delta", 0))
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid delta"}, status=400)

    ing = get_object_or_404(Ingredient, id=ingredient_id)

    new_qty = (ing.quantity or 0) + delta
    if new_qty <= 0:
        deleted_qty = ing.quantity
        ing.delete()
        return JsonResponse({"ok": True, "new_quantity": 0, "deleted": True, "deleted_qty": deleted_qty})
    else:
        ing.quantity = new_qty
        ing.save(update_fields=["quantity"])
        return JsonResponse({"ok": True, "new_quantity": ing.quantity, "deleted": False})
    
def pick_queryset_for_policy(qs, policy: str, target_date: str | None = None):
    policy = (policy or "oldest").lower()

    if policy == "newest":
        return qs.order_by("-created_at", "-prepared_date", "-id")

    if policy == "nearest_expiry":
        def days_remaining(e):
            if not e: 
                return 10**9
            if isinstance(e, str):
                try:
                    e = _date.fromisoformat(e)
                except Exception:
                    return 10**9
            return (e - _date.today()).days
        items = list(qs)
        items.sort(key=lambda x: days_remaining(x.expiry_date))
        return items  # คืน list ได้

    # ✅ เพิ่มเคสนี้
    if policy == "expired_only":
        return qs.filter(expiry_date__lt=_date.today()).order_by("expiry_date", "created_at", "id")

    if policy == "by_date" and target_date:
        try:
            dt = _date.fromisoformat(target_date)
        except Exception:
            dt = None
        if dt:
            return qs.filter(expiry_date=dt).order_by("created_at", "id")

    # default
    return qs.order_by("created_at", "prepared_date", "id")

@require_GET
def api_lot_probe(request):
    """
    GET /api/lots/?name=นมสด
    คืนข้อมูลคร่าวๆ เพื่อถามผู้ใช้ว่าจะลบล็อตแบบไหน
    """
    name = (request.GET.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "missing name"}, status=400)

    qs = Ingredient.objects.filter(name__iexact=name).order_by("created_at")
    n = qs.count()
    if n == 0:
        return JsonResponse({"ok": False, "error": "not found"}, status=404)

    # ตัวอย่างข้อมูลประกอบการพูด
    oldest = qs.first()
    newest = qs.order_by("-created_at").first()

    # ใกล้หมดอายุ (บางล็อตอาจไม่มีวันหมดอายุ)
    def days_remaining(d):
        if not d: return 10**9
        if isinstance(d, str):
            try: d = _date.fromisoformat(d)
            except: return 10**9
        return (d - timezone.localdate()).days

    items = list(qs)
    items.sort(key=lambda x: days_remaining(x.expiry_date))
    near = items[0] if items else None

    expired_count = qs.filter(expiry_date__lt=timezone.localdate()).count()

    return JsonResponse({
        "ok": True,
        "name": name,
        "lots": n,
        "has_expired": expired_count > 0,
        "oldest_created": oldest.created_at.isoformat() if oldest else None,
        "newest_created": newest.created_at.isoformat() if newest else None,
        "nearest_expiry": (near.expiry_date.isoformat() if (near and near.expiry_date) else None),
    })

def _norm_th(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u200b", "")          # ลบ Zero-width space
    s = re.sub(r"[\s\(\)\[\]{}]", "", s)
    return s


HOWTO_DB = None
HOWTO_MTIME = None

def _howto_path():
    p = Path(settings.BASE_DIR) / "index" / "howto.json"
    return p

def _load_howto_db():
    global HOWTO_DB, HOWTO_MTIME
    path = _howto_path()
    # ถ้าไฟล์ไม่มี ให้คืน structure ว่างแทน (ไม่เรียก API ภายนอก)
    if not path.exists():
        HOWTO_DB = {"recipes": {}, "aliases": {}}
        HOWTO_MTIME = None
        return HOWTO_DB
    try:
        mtime = path.stat().st_mtime
        # โหลดใหม่เฉพาะเมื่อไฟล์เปลี่ยนหรือยังไม่เคยโหลด
        if HOWTO_DB is None or HOWTO_MTIME != mtime:
            with path.open("r", encoding="utf-8") as f:
                HOWTO_DB = json.load(f)
            HOWTO_MTIME = mtime
        return HOWTO_DB
    except Exception:
        HOWTO_DB = {"recipes": {}, "aliases": {}}
        HOWTO_MTIME = None
        return HOWTO_DB

def _norm_th(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u200b", "")          # ลบ Zero-width space
    s = re.sub(r"[\s\(\)\[\]{}]", "", s)
    return s

def api_recipes(request):
    """อ่านและส่งข้อมูลสูตรอาหารจาก thai_recipes.json"""
    json_path = Path(__file__).parent / 'thai_recipes.json'
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def api_howto(request):
    """อ่านและส่งข้อมูลวิธีทำอาหารจาก howto.json"""
    json_path = Path(__file__).parent / 'howto.json'
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

HOWTO_PATH = os.path.join(settings.BASE_DIR, "index", "howto.json")

def _load_howto():
    with open(HOWTO_PATH, encoding="utf-8") as f:
        return json.load(f)

def _norm(s: str) -> str:
    return (s or "").strip().lower().replace("\u00A0", " ")  # เผื่อมี non-breaking space

@require_GET
def api_howto_all(request):
    """
    ส่งคืนทั้งไฟล์ howto.json (รองรับรูปแบบ object หรือ array)
    """
    try:
        data = _load_howto()
        # อนุญาตให้เป็น object หรือ array ก็ได้
        return JsonResponse(data, safe=isinstance(data, list))
    except FileNotFoundError:
        raise Http404("howto.json not found")

@require_GET
def api_howto(request):
    """
    ค้นหาวิธีทำตามชื่อเมนู ?q=
    - รองรับไฟล์แบบ object ที่ key=ชื่อเมนู
    - หรือ array [{title/name, ingredients, steps, videos}]
    """
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"ok": False, "error": "missing q"}, status=400)

    try:
        data = _load_howto()
    except FileNotFoundError:
        raise Http404("howto.json not found")

    want = _norm(q)
    found = None

    if isinstance(data, dict):
        # 1) ตรง key
        for k, v in data.items():
            if _norm(k) == want:
                found = v
                break
        # 2) ตรง title/name ภายใน
        if not found:
            for v in data.values():
                t = _norm((v.get("title") or v.get("name") or ""))
                if t == want:
                    found = v
                    break
    elif isinstance(data, list):
        for v in data:
            t = _norm((v.get("title") or v.get("name") or ""))
            if t == want:
                found = v
                break

    if not found:
        return JsonResponse({"ok": False, "error": f"not found: {q}"}, status=404)

    resp = {
        "ok": True,
        "title": found.get("title") or found.get("name") or q,
        "ingredients": found.get("ingredients", []),
        "steps": found.get("steps", []),
        "videos": found.get("videos", []),
    }
    return JsonResponse(resp)