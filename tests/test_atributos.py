import pytest
from src.transform import atributos as a

# (nombre, marca_tienda, marca, modelo, almacenamiento, condicion)
CASOS = [
    ("Celular SAMSUNG Galaxy A57 256GB 5G Morado", "", "Samsung", "a57", 256, "nuevo"),
    ("Celular Galaxy A55 5G 256GB Azul Oscuro Nuevo", "SAMSUNG", "Samsung", "a55", 256, "nuevo"),
    ("Celular Galaxy A55 5G 256Gb Lila Reacondicionado +14 Meses", "SAMSUNG", "Samsung", "a55", 256, "reacondicionado"),
    ("Samsung Galaxy S24 Ultra 512GB Negro", "", "Samsung", "s24 ultra", 512, "nuevo"),
    ("Celular SAMSUNG Galaxy S26Ultra 512GB 5G Negro", "", "Samsung", "s26 ultra", 512, "nuevo"),
    ("Samsung Galaxy A56 5G 256Gb Ram 12Gb Negro", "", "Samsung", "a56", 256, "nuevo"),
    ("Celular Galaxy Z Flip6 256GB Azul", "SAMSUNG", "Samsung", "z flip6", 256, "nuevo"),
    ("Apple iPhone 15 Pro Max 256GB Titanio Natural", "", "Apple", "iphone 15 pro max", 256, "nuevo"),
    ("iPhone 13 128GB Medianoche", "APPLE", "Apple", "iphone 13", 128, "nuevo"),
    ("Celular XIAOMI Redmi Note 13 Pro 256GB 5G Negro", "", "Xiaomi", "redmi note 13 pro", 256, "nuevo"),
    ("Celular Xiaomi Redmi 13C 128GB Azul", "", "Xiaomi", "redmi 13c", 128, "nuevo"),
    ("Celular POCO X6 Pro 512GB", "XIAOMI", "Xiaomi", "poco x6 pro", 512, "nuevo"),
    ("Celular MOTOROLA Moto G24 128GB Gris", "", "Motorola", "g24", 128, "nuevo"),
    ("Celular Motorola Edge 50 Fusion 256GB", "", "Motorola", "edge 50 fusion", 256, "nuevo"),
    ("Celular HONOR X7c 256GB Verde", "", "Honor", "x7c", 256, "nuevo"),
    ("Celular Honor 200 Lite 5G 256GB", "", "Honor", "200 lite", 256, "nuevo"),
    ("Celular INFINIX Hot 40i 128GB Negro", "", "Infinix", "hot 40i", 128, "nuevo"),
    ("Celular Infinix Note 50s 256GB Rojo", "", "Infinix", "note 50s", 256, "nuevo"),
    ("Celular TECNO Spark 20 Pro 256GB", "", "Tecno", "spark 20 pro", 256, "nuevo"),
    ("Celular OPPO Reno 12 5G 512GB", "", "Oppo", "reno 12", 512, "nuevo"),
    ("Celular OPPO A38 128GB Negro", "", "Oppo", "a38", 128, "nuevo"),
    ("Celular Realme C63 256GB Verde", "", "Realme", "c63", 256, "nuevo"),
]


@pytest.mark.parametrize("nombre,marca_t,marca,modelo,gb,cond", CASOS)
def test_atributos(nombre, marca_t, marca, modelo, gb, cond):
    m = a.detectar_marca(nombre, marca_t)
    assert m == marca
    assert a.detectar_modelo(nombre, m) == modelo
    assert a.detectar_almacenamiento(nombre) == gb
    assert a.detectar_condicion(nombre) == cond


def test_ram_no_se_confunde_con_almacenamiento():
    assert a.detectar_almacenamiento("Galaxy A56 5G 8GB Ram 256Gb") == 256
    assert a.detectar_ram("Galaxy A56 5G 8GB Ram 256Gb") == 8


@pytest.mark.parametrize("nombre", ["Funda para Samsung Galaxy A55", "Cargador Apple 20W", "Smartwatch Xiaomi Band 8",
                                    "Protector de pantalla iPhone 15"])
def test_accesorios_se_descartan(nombre):
    assert not a.es_celular(nombre)


# (nombre, marca_tienda, marca, pulgadas, modelo, combo): el mismo TV escrito como lo publica cada tienda
CASOS_TV = [
    ('TV SAMSUNG 65" Pulgadas 165,1 cm 65U8000H 4K-UHD LED Crystal Smart TV con IA', "", "Samsung", 65, "65u8000h", False),
    ("Televisor SAMSUNG 65 pulgadas LED Uhd4K Smart TV UN65U8000HKXZL", "SAMSUNG", "Samsung", 65, "65u8000h", False),
    ("Televisor 40″ QLED QN40Q5FAAK Full HD Smart TV Tizen", "SAMSUNG", "Samsung", 40, "40q5f", False),
    ("Televisor 43′ 4K UHD Crystal Smart Tv UN43U8000FK", "SAMSUNG", "Samsung", 43, "43u8000f", False),
    ("Televisor Samusng 65\" The Frame Qn65Ls03Hekxzl + Marco Vg-Scfh65Tkbzx", "SAMSUNG", "Samsung", 65, "65ls03h", True),
    ('TV SAMSUNG 55" Pulgadas 139,7 cm 55M75H 4K-UHD Mini LED Smart TV con IA + Barra de sonido SAMSUNG HW-B400F/ZL',
     "", "Samsung", 55, "55m75h", True),
    ("Televisor LG 55 pulgadas OLED evo 4K OLED55C4PSA", "LG", "LG", 55, "55c4p", False),
    ("Televisor SONY 55 pulgadas KD-55X77L", "", "Sony", 55, "55x77l", False),
    ("Televisor I Samsung I 65 Pulgadas I 4K I Mini LED I 75H + BARRA", "SAMSUNG", "Samsung", 65, None, True),
]


@pytest.mark.parametrize("nombre,marca_t,marca,pulgadas,modelo,combo", CASOS_TV)
def test_atributos_tv(nombre, marca_t, marca, pulgadas, modelo, combo):
    assert a.es_televisor(nombre)
    assert a.detectar_marca(nombre, marca_t) == marca
    assert a.detectar_pulgadas(nombre) == pulgadas
    assert a.detectar_modelo_tv(nombre, pulgadas) == modelo
    assert a.es_combo(nombre) == combo


@pytest.mark.parametrize("nombre", ["Soporte para TV 32 a 70 pulgadas", "Control remoto para televisor Samsung",
                                    "Barra de sonido Samsung HW-B400F"])
def test_accesorios_tv_se_descartan(nombre):
    assert not a.es_televisor(nombre)
