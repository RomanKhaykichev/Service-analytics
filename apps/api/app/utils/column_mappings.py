# -*- coding: utf-8 -*-
"""
Canonical column names = RU (current backend). UZ (and other) headers are mapped to canonical on import.
Language is auto-detected from headers; no UI selection.
"""
from typing import Dict, List, Tuple, Set

# ---------------------------------------------------------------------------
# Canonical (RU) column names per file_type (keys of *_MAP in imports.py)
# ---------------------------------------------------------------------------
CANONICAL_SALES = {
    "Статус", "Дата создания", "Дата получения", "№ заказа", "Штрихкод", "SKU",
    "Наименование", "Категория", "Количество", "Возвраты", "Выручка (сумы)",
    "Выручка с вычетом комиссии и логистики (сумы)", "Комиссия маркетплейса (сумы)",
    "Цена (сумы)", "Промокод (сумы)", "Себестоимость (сумы)", "Логистический сбор",
}

# Column order in Uzum sells-report XLSX (header row 2 in cabinet export).
SALES_COLUMN_ORDER = [
    "Статус",
    "Дата создания",
    "Дата получения",
    "№ заказа",
    "Штрихкод",
    "SKU",
    "Наименование",
    "Категория",
    "Количество",
    "Возвраты",
    "Выручка (сумы)",
    "Выручка с вычетом комиссии и логистики (сумы)",
    "Комиссия маркетплейса (сумы)",
    "Цена (сумы)",
    "Промокод (сумы)",
    "Себестоимость (сумы)",
    "Логистический сбор",
]

CANONICAL_EXPENSES = {
    "Магазины",
    "Источник",
    "Услуга",
    "Статус",
    "ID операции",
    "Дата списания",
    "Стоимость (сумы)",
    "Количество",
    "Сумма (сумы)",
    "Тип операции",
}

# Column order in Uzum expenses-report XLSX (header row 2 in cabinet export).
EXPENSES_COLUMN_ORDER = [
    "Магазины",
    "Источник",
    "Услуга",
    "Статус",
    "ID операции",
    "Дата списания",
    "Стоимость (сумы)",
    "Количество",
    "Сумма (сумы)",
    "Тип операции",
]
CANONICAL_LEFTOUT = {
    "Магазин", "Название товара", "ID товара", "SKU", "Штрихкод", "Заканчивается",
    "Индикатор обеспеченности", "Плановая дата, когда закончатся текущие остатки",
    "Обеспеченность (на сколько дней хватит текущих остатков), дней",
    "Рекомендованное количество на поставку, шт", "На вашей стороне (на складе FBS), шт",
    "На стороне маркетплейса (всего в продаже, в пути, на складах и фотостудии), шт",
    "В поставке (создана накладная), шт", "В продаже, шт", "В пути до клиента (в логистике), шт",
    "В пути от клиента (возвраты и отказы), шт", "На складе длительного хранения (СДХ), шт",
    "На фотостудии, шт", "Брак на складе, шт",
    "Потенциальная сумма к получению за 1 шт, сум",
    "Потенциальная сумма к получению за все остатки, сум",
}
CANONICAL_STORAGE = {
    "Магазин",
    "Название товара",
    "ID товара",
    "SKU",
    "Штрихкод",
    "Габаритная группа",
    "Среднесуточные остатки FBO за 15 дней, шт",
    "Среднесуточные продажи FBO за 15 дней, шт",
    "Оборачиваемость, дней",
    "Хранение",
    "За хранение 1 единицы 1 день, сум",
    "Остатки FBO (всего в продаже и на СДХ), шт",
    "Всего за хранение 1 день, сум",
    "Всего за хранение последние 30 дней, сум",
}

# Column order in Uzum seller-storage-report XLSX (header row 2).
STORAGE_COLUMN_ORDER = [
    "Магазин",
    "Название товара",
    "ID товара",
    "SKU",
    "Штрихкод",
    "Габаритная группа",
    "Среднесуточные остатки FBO за 15 дней, шт",
    "Среднесуточные продажи FBO за 15 дней, шт",
    "Оборачиваемость, дней",
    "Хранение",
    "За хранение 1 единицы 1 день, сум",
    "Остатки FBO (всего в продаже и на СДХ), шт",
    "Всего за хранение 1 день, сум",
    "Всего за хранение последние 30 дней, сум",
]
CANONICAL_LEFTOUT_OLD = {
    "Штрихкод", "SKU", "ID товара", "Наименование", "В продаже",
    "Себест. (сумы)", "Стоимость продажи (сумы)", "Оборачиваемость, дней",
    "Стоимость хранения 1 дня, сум",
    "Среднесуточные продажи", "Среднесуточные продажи FBO за 15 дней, шт",
    "К отправке", "Общий остаток",
    "Ссылка на товар",
}

# Uzum left-out-report (старый формат / загрузка в сервис) — порядок как в кабинете.
CANONICAL_LEFTOUT_API = {
    "ID",
    "Наименование",
    "Штрихкод",
    "SKU",
    "ID товара",
    "К отправке",
    "В продаже",
    "Остаток FBS",
    "Возврат",
    "Брак",
    "Себест. (сумы)",
    "Стоимость продажи (сумы)",
    "Общий остаток",
    "Общая сумма остатков (сумы)",
    "Себест. (сумма) (сумы)",
    "Стоимость продажи (сумма) (сумы)",
    "Остаток на СДХ",
    "Остаток на фотостудии",
    "Остаток на СДХ (сумма) (сумы)",
    "Доступно к отправке",
    "Статус",
    "Габаритная группа",
    "Среднесуточные остатки",
    "Среднесуточные продажи",
    "Оборачиваемость",
    "Хранение",
    "Тариф, сум",
    "Стоимость хранения 1 дня, сум",
    "Ссылка на товар",
    "Рейтинг",
    "Количество отзывов",
}

LEFTOUT_API_COLUMN_ORDER = [
    "ID",
    "Наименование",
    "Штрихкод",
    "SKU",
    "ID товара",
    "К отправке",
    "В продаже",
    "Остаток FBS",
    "Возврат",
    "Брак",
    "Себест. (сумы)",
    "Стоимость продажи (сумы)",
    "Общий остаток",
    "Общая сумма остатков (сумы)",
    "Себест. (сумма) (сумы)",
    "Стоимость продажи (сумма) (сумы)",
    "Остаток на СДХ",
    "Остаток на фотостудии",
    "Остаток на СДХ (сумма) (сумы)",
    "Доступно к отправке",
    "Статус",
    "Габаритная группа",
    "Среднесуточные остатки",
    "Среднесуточные продажи",
    "Оборачиваемость",
    "Хранение",
    "Тариф, сум",
    "Стоимость хранения 1 дня, сум",
    "Ссылка на товар",
    "Рейтинг",
    "Количество отзывов",
]

CANONICAL_BY_FILE_TYPE: Dict[str, Set[str]] = {
    "sales": CANONICAL_SALES,
    "expenses": CANONICAL_EXPENSES,
    "leftout": CANONICAL_LEFTOUT,
    "storage": CANONICAL_STORAGE,
    "leftout_old": CANONICAL_LEFTOUT_OLD,
}

# ---------------------------------------------------------------------------
# UZ (normalized lowercase) -> canonical RU. Extend per your UZ export samples.
# Normalization: trim, collapse spaces, lowercase for lookup.
# ---------------------------------------------------------------------------
def _n(s: str) -> str:
    s = str(s).replace("\n", " ").replace("\r", " ").replace("\u00a0", " ")
    s = s.replace("\u02bb", "'")   # U+02BB modifier letter turned comma (soʻm)
    s = s.replace("\u2019", "'")   # U+2019 right single quotation mark (Do‘kon)
    s = s.replace("\u2018", "'")   # U+2018 left single quotation mark
    return " ".join(s.strip().lower().split())

# Sales (Отчет по продажам) — UZ headers -> RU canonical
# Варианты из выгрузок UZUM: Yaratilish sanasi, Tushim (soʻm), Narxi (soʻm) и т.д.
UZ_TO_RU_SALES: Dict[str, str] = {
    _n("Holat"): "Статус",
    _n("Holati"): "Статус",
    _n("Yaratilgan sana"): "Дата создания",
    _n("Yaratilish sanasi"): "Дата создания",
    _n("Qabul qilingan sana"): "Дата получения",
    _n("Olinish sanasi"): "Дата получения",
    _n("Buyurtma raqami"): "№ заказа",
    _n("Shtrix kod"): "Штрихкод",
    _n("Shtrix-kod"): "Штрихкод",
    _n("Shtrixkod"): "Штрихкод",
    _n("SKU"): "SKU",
    _n("Mahsulot nomi"): "Наименование",
    _n("Nomi"): "Наименование",
    _n("Kategoriya"): "Категория",
    _n("Turkumi"): "Категория",
    _n("Miqdor"): "Количество",
    _n("Soni"): "Количество",
    _n("Qaytishlar"): "Возвраты",
    _n("Qaytarishlar"): "Возвраты",
    _n("Daromad (so'm)"): "Выручка (сумы)",
    _n("Daromad (soʻm)"): "Выручка (сумы)",
    _n("Tushim (so'm)"): "Выручка (сумы)",
    _n("Tushim (soʻm)"): "Выручка (сумы)",
    _n("Komissiya va logistika chegirilgach daromad (so'm)"): "Выручка с вычетом комиссии и логистики (сумы)",
    _n("Komissiya va logistika chiqarib tashlangan tushim (so'm)"): "Выручка с вычетом комиссии и логистики (сумы)",
    _n("Komissiya va logistika chiqarib tashlangan tushim (soʻm)"): "Выручка с вычетом комиссии и логистики (сумы)",
    _n("Marketpleys komissiyasi (so'm)"): "Комиссия маркетплейса (сумы)",
    _n("Marketpleys komissiyasi (soʻm)"): "Комиссия маркетплейса (сумы)",
    _n("Narx (so'm)"): "Цена (сумы)",
    _n("Narxi (so'm)"): "Цена (сумы)",
    _n("Narxi (soʻm)"): "Цена (сумы)",
    _n("Promokod (so'm)"): "Промокод (сумы)",
    _n("Promokod (soʻm)"): "Промокод (сумы)",
    _n("O'ziga tushish narxi (so'm)"): "Себестоимость (сумы)",
    _n("Oziga tushish narxi (so'm)"): "Себестоимость (сумы)",
    _n("Tannarxi (so'm)"): "Себестоимость (сумы)",
    _n("Tannarxi (soʻm)"): "Себестоимость (сумы)",
    _n("Logistika to'lovi"): "Логистический сбор",
}

# Expenses (Отчет по услугам) — варианты UZUM (Yechilish sanasi, Qiymati (soʻm))
UZ_TO_RU_EXPENSES: Dict[str, str] = {
    _n("Do'kon"): "Магазины",
    _n("Dokon"): "Магазины",
    _n("Do'konlar"): "Магазины",
    _n("Do'kon nomi"): "Магазины",
    _n("Manba"): "Источник",
    _n("Xizmat"): "Услуга",
    _n("Holat"): "Статус",
    _n("Holati"): "Статус",
    _n("Operatsiya ID"): "ID операции",
    _n("Operatsiya id"): "ID операции",
    _n("Operatsiya Id"): "ID операции",
    _n("Amal ID"): "ID операции",
    _n("Amal identifikatori"): "ID операции",
    _n("Hisobdan chiqarilgan sana"): "Дата списания",
    _n("Hisobdan chiqarilish sanasi"): "Дата списания",
    _n("Chiqarilish sanasi"): "Дата списания",
    _n("Yechilish sanasi"): "Дата списания",
    _n("Narx (so'm)"): "Стоимость (сумы)",
    _n("Narx (soʻm)"): "Стоимость (сумы)",
    _n("Narxi (so'm)"): "Стоимость (сумы)",
    _n("Narxi (soʻm)"): "Стоимость (сумы)",
    _n("Qiymati (so'm)"): "Стоимость (сумы)",
    _n("Qiymati (soʻm)"): "Стоимость (сумы)",
    _n("Miqdor"): "Количество",
    _n("Soni"): "Количество",
    _n("Summa (so'm)"): "Сумма (сумы)",
    _n("Summa (soʻm)"): "Сумма (сумы)",
    _n("Tushim (so'm)"): "Сумма (сумы)",
    _n("Tushim (soʻm)"): "Сумма (сумы)",
    _n("Operatsiya turi"): "Тип операции",
}

# Leftout (Остатки новый) / Inventory — варианты UZUM
UZ_TO_RU_LEFTOUT: Dict[str, str] = {
    _n("Do'kon"): "Магазин",
    _n("Dokon"): "Магазин",
    _n("Do'kon nomi"): "Магазин",
    _n("Mahsulot nomi"): "Название товара",
    _n("Nomi"): "Название товара",
    _n("Mahsulot ID"): "ID товара",
    _n("Mahsulot Id"): "ID товара",
    _n("Tovar identifikatori"): "ID товара",
    _n("SKU"): "SKU",
    _n("Shtrix kod"): "Штрихкод",
    _n("Shtrix-kod"): "Штрихкод",
    _n("Shtrixkod"): "Штрихкод",
    _n("Tugaydi"): "Заканчивается",
    _n("Ta'minot ko'rsatkichi"): "Индикатор обеспеченности",
    _n("Rejalashtirilgan tugash sanasi"): "Плановая дата, когда закончатся текущие остатки",
    _n("Ta'minot (kun)"): "Обеспеченность (на сколько дней хватит текущих остатков), дней",
    _n("Yetkazib berish uchun tavsiya etilgan miqdor"): "Рекомендованное количество на поставку, шт",
    _n("Sizning tomoningizda (FBS omborida)"): "На вашей стороне (на складе FBS), шт",
    _n("Marketpleys tomonda (jami sotuvda, yo'lda, omborlarda)"): "На стороне маркетплейса (всего в продаже, в пути, на складах и фотостудии), шт",
    _n("Yetkazib berishda (nakladnoy yaratilgan)"): "В поставке (создана накладная), шт",
    _n("Sotuvda"): "В продаже, шт",
    _n("Mijozga yo'lda (logistikada)"): "В пути до клиента (в логистике), шт",
    _n("Mijozdan yo'lda (qaytishlar)"): "В пути от клиента (возвраты и отказы), шт",
    _n("Uzoq muddatli saqlash omborida"): "На складе длительного хранения (СДХ), шт",
    _n("Fotos studiyada"): "На фотостудии, шт",
    _n("Ombordagi nuqson"): "Брак на складе, шт",
    _n("1 dona uchun olinadigan summa (so'm)"): "Потенциальная сумма к получению за 1 шт, сум",
    _n("1 dona uchun olinadigan summa (soʻm)"): "Потенциальная сумма к получению за 1 шт, сум",
    _n("Barcha qoldiqlar uchun olinadigan summa (so'm)"): "Потенциальная сумма к получению за все остатки, сум",
    _n("Barcha qoldiqlar uchun olinadigan summa (soʻm)"): "Потенциальная сумма к получению за все остатки, сум",
    _n("Sotuvda"): "В продаже, шт",
}

# Storage (Отчет по хранению) / seller — варианты UZUM (Do'kon, Tovarning nomi, Gabarit guruhi)
UZ_TO_RU_STORAGE: Dict[str, str] = {
    _n("Do'kon"): "Магазин",
    _n("Dokon"): "Магазин",
    _n("Do'kon nomi"): "Магазин",
    _n("Mahsulot nomi"): "Название товара",
    _n("Nomi"): "Название товара",
    _n("Tovarning nomi"): "Название товара",
    _n("Mahsulot ID"): "ID товара",
    _n("Mahsulot Id"): "ID товара",
    _n("Tovarning ID"): "ID товара",
    _n("Tovarning Id"): "ID товара",
    _n("SKU"): "SKU",
    _n("Shtrix kod"): "Штрихкод",
    _n("Shtrix-kod"): "Штрихкод",
    _n("Shtrixkod"): "Штрихкод",
    _n("O'lchov guruhi"): "Габаритная группа",
    _n("Olchov guruhi"): "Габаритная группа",
    _n("Gabarit guruhi"): "Габаритная группа",
    _n("O'lchamlar guruhi"): "Габаритная группа",
    _n("Aylanish (kun)"): "Оборачиваемость, дней",
    _n("Aylanma, kunlar"): "Оборачиваемость, дней",
    _n("Saqlash"): "Хранение",
    _n("15 kun ichida FBO o'rtacha kunlik qoldiqlari, dona"): "Среднесуточные остатки FBO за 15 дней, шт",
    _n("15 kun ichida FBO oʻrtacha kunlik qoldiqlari, dona"): "Среднесуточные остатки FBO за 15 дней, шт",
    _n("15 kun ichida FBO o'rtacha kunlik sotuvlari, dona"): "Среднесуточные продажи FBO за 15 дней, шт",
    _n("15 kun ichida FBO oʻrtacha kunlik sotuvlari, dona"): "Среднесуточные продажи FBO за 15 дней, шт",
    _n("Aylanma, kunlar"): "Оборачиваемость, дней",
    _n("Aylanish (kun)"): "Оборачиваемость, дней",
    _n("1 ta birlikni 1 kun saqlash evaziga, so'm"): "За хранение 1 единицы 1 день, сум",
    _n("1 ta birlikni 1 kun saqlash evaziga, soʻm"): "За хранение 1 единицы 1 день, сум",
    _n("FBO qoldiqlari (jami sotuvda va OUMSda), dona"): "Остатки FBO (всего в продаже и на СДХ), шт",
    _n("FBO qoldiqlari  (jami sotuvda va OUMSda), dona"): "Остатки FBO (всего в продаже и на СДХ), шт",
    _n("1 kun saqlash evaziga jami, so'm"): "Всего за хранение 1 день, сум",
    _n("1 kun saqlash evaziga jami, soʻm"): "Всего за хранение 1 день, сум",
    _n("Oxirgi 30 kun uchun jami saqlash (so'm)"): "Всего за хранение последние 30 дней, сум",
    _n("Oxirgi 30 kun uchun jami saqlash (soʻm)"): "Всего за хранение последние 30 дней, сум",
    _n("Oxirgi 30 kun saqlash evaziga jami, so'm"): "Всего за хранение последние 30 дней, сум",
    _n("Oxirgi 30 kun saqlash evaziga jami, soʻm"): "Всего за хранение последние 30 дней, сум",
}

# Leftout old (Остатки старый) — варианты UZUM
UZ_TO_RU_LEFTOUT_OLD: Dict[str, str] = {
    _n("Shtrix kod"): "Штрихкод",
    _n("Shtrix-kod"): "Штрихкод",
    _n("Shtrixkod"): "Штрихкод",
    _n("SKU"): "SKU",
    _n("Mahsulot ID"): "ID товара",
    _n("Mahsulot Id"): "ID товара",
    _n("Tovar identifikatori"): "ID товара",
    _n("Mahsulot nomi"): "Наименование",
    _n("Nomi"): "Наименование",
    _n("Sotuvda"): "В продаже",
    _n("O'ziga tushish (so'm)"): "Себест. (сумы)",
    _n("O'ziga tushish (soʻm)"): "Себест. (сумы)",
    _n("Oziga tushish (so'm)"): "Себест. (сумы)",
    _n("Tannarxi (so'm)"): "Себест. (сумы)",
    _n("Tannarxi (soʻm)"): "Себест. (сумы)",
    _n("Sotuv narxi (so'm)"): "Стоимость продажи (сумы)",
    _n("Sotuv narxi (soʻm)"): "Стоимость продажи (сумы)",
    _n("Sotuv qiymati (so'm)"): "Стоимость продажи (сумы)",
    _n("Sotuv qiymati (soʻm)"): "Стоимость продажи (сумы)",
    _n("Sotuv qiymati (summa) (so'm)"): "Стоимость продажи (сумы)",
    _n("Sotuv qiymati (summa) (soʻm)"): "Стоимость продажи (сумы)",
    # Стоимость хранения за 1 день (узбекские варианты)
    _n("1 kunlik saqlash qiymati, so'm"): "Стоимость хранения 1 дня, сум",
    _n("1 kunlik saqlash qiymati, soʻm"): "Стоимость хранения 1 дня, сум",
    _n("1 kunlik saqlash narxi (so'm)"): "Стоимость хранения 1 дня, сум",
    _n("1 kunlik saqlash narxi (soʻm)"): "Стоимость хранения 1 дня, сум",
    _n("Saqlash narxi 1 kun, so'm"): "Стоимость хранения 1 дня, сум",
    _n("Saqlash narxi 1 kun, soʻm"): "Стоимость хранения 1 дня, сум",
    _n("1 ta birlikni 1 kun saqlash evaziga, so'm"): "Стоимость хранения 1 дня, сум",
    _n("1 ta birlikni 1 kun saqlash evaziga, so‘m"): "Стоимость хранения 1 дня, сум",
    _n("Mahsulot havolasi"): "Ссылка на товар",
    _n("Tovar havolasi"): "Ссылка на товар",
    _n("1 ta birlikni 1 kun saqlash evaziga, soʻm"): "Стоимость хранения 1 дня, сум",
    # Оборачиваемость (дней) — для рекомендаций по отгрузке и расчётов
    _n("Aylanib turish"): "Оборачиваемость, дней",
    _n("Aylanma, kunlar"): "Оборачиваемость, дней",
    _n("Aylanish (kun)"): "Оборачиваемость, дней",
    # Продаж в день / Запланировано к отгрузке — для рекомендаций по отгрузке
    _n("Sutkalik o'rtacha sotuvlar"): "Среднесуточные продажи",
    _n("Sutkalik oʻrtacha sotuvlar"): "Среднесуточные продажи",
    _n("15 kun ichida FBO o'rtacha kunlik sotuvlari, dona"): "Среднесуточные продажи FBO за 15 дней, шт",
    _n("15 kun ichida FBO oʻrtacha kunlik sotuvlari, dona"): "Среднесуточные продажи FBO за 15 дней, шт",
    _n("Yuborishga"): "К отправке",
    _n("Yuborishga mavjud"): "К отправке",
    _n("Umumiy qoldiq"): "Общий остаток",
}

UZ_TO_RU_BY_FILE_TYPE: Dict[str, Dict[str, str]] = {
    "sales": UZ_TO_RU_SALES,
    "expenses": UZ_TO_RU_EXPENSES,
    "leftout": UZ_TO_RU_LEFTOUT,
    "storage": UZ_TO_RU_STORAGE,
    "leftout_old": UZ_TO_RU_LEFTOUT_OLD,
}


def normalize_header(h: str) -> str:
    """Trim, collapse spaces, preserve case (for canonical match)."""
    if h is None:
        return ""
    s = str(h).replace("\n", " ").replace("\r", " ").replace("\u00a0", " ")
    return " ".join(s.strip().split())


def normalize_header_lower(h: str) -> str:
    """Trim, collapse spaces, lowercase (for UZ lookup). Normalize apostrophe-like chars to '."""
    s = normalize_header(h).lower()
    s = s.replace("\u02bb", "'").replace("\u2019", "'").replace("\u2018", "'")
    return s


def _uz_lookup_variants(h: str) -> List[str]:
    """Return list of normalized variants for flexible UZ lookup (hyphen/underscore/apostrophe)."""
    base = normalize_header_lower(h)
    if not base:
        return []
    variants = [base]
    # hyphen/underscore -> space (Shtrix-kod vs Shtrix kod)
    for char in "-_":
        if char in base:
            variants.append(" ".join(base.replace(char, " ").split()))
    # apostrophe variants (O'ziga vs Oziga)
    if "'" in base:
        variants.append(base.replace("'", ""))
    return list(dict.fromkeys(variants))  # preserve order, no duplicates


class HeaderMappingError(Exception):
    """Base for mapping errors."""
    pass


class DuplicateCanonicalError(HeaderMappingError):
    """Two different source headers map to the same canonical column."""
    def __init__(self, canonical: str, sources: List[str]):
        self.canonical = canonical
        self.sources = sources
        super().__init__(f"Конфликт: одна и та же колонка '{canonical}' задана разными заголовками: {sources}")


class MissingRequiredColumnsError(HeaderMappingError):
    """Required canonical columns are missing after mapping."""
    def __init__(
        self,
        missing: List[str],
        file_type: str,
        possible_uz: Dict[str, List[str]],
        possible_ru: Set[str],
        found_headers: List[str] | None = None,
    ):
        self.missing = missing
        self.file_type = file_type
        self.possible_uz = possible_uz
        self.possible_ru = possible_ru
        self.found_headers = found_headers or []
        uz_hint = "; ".join(f"{c} (UZ: {list(possible_uz.get(c, []))})" for c in missing)
        msg = (
            f"[{file_type}] Не найдены обязательные колонки: {missing}. "
            f"Ожидаются (RU): {missing}. Варианты UZ в маппинге: {uz_hint}."
        )
        if self.found_headers:
            msg += f" Найдены заголовки в файле: {self.found_headers}"
        super().__init__(msg)


def detect_language(file_type: str, normalized_headers: List[str]) -> str:
    """
    Detect RU vs UZ from headers. Returns 'ru' or 'uz'.
    If any header is in UZ mapping -> uz; else if any in canonical -> ru; else ru (default).
    """
    canonical_set = CANONICAL_BY_FILE_TYPE.get(file_type, set())
    uz_map = UZ_TO_RU_BY_FILE_TYPE.get(file_type, {})
    lower_headers = [normalize_header_lower(h) for h in normalized_headers]
    ru_count = sum(1 for h in normalized_headers if h in canonical_set)
    uz_count = sum(1 for h in lower_headers if h in uz_map)
    return "uz" if uz_count > ru_count else "ru"


def map_headers_to_canonical(
    file_type: str,
    normalized_headers: List[str],
    required_canonical: List[str],
) -> Tuple[Dict[str, str], str]:
    """
    Build rename dict: current_header -> canonical (RU) name.
    - If header is already canonical (RU), keep as-is.
    - Else if header (normalized lower) is in UZ map, use mapped canonical.
    - Else column is unknown; we do not rename (will be dropped or ignored by staging).
    Returns (rename_dict, detected_language).
    Raises DuplicateCanonicalError if two headers map to same canonical.
    Raises MissingRequiredColumnsError if required canonical columns are missing after mapping.
    """
    canonical_set = CANONICAL_BY_FILE_TYPE.get(file_type, set())
    uz_map = UZ_TO_RU_BY_FILE_TYPE.get(file_type, {})
    rename: Dict[str, str] = {}
    assigned_canonical: Set[str] = set()

    for h in normalized_headers:
        if not h:
            continue
        if h in canonical_set:
            canonical = h
        else:
            canonical = None
            for variant in _uz_lookup_variants(h):
                if variant in uz_map:
                    canonical = uz_map[variant]
                    break
            # RU: tolerate common Excel header variants for left-out-report_old.
            # (Backend expects canonical RU keys like "Оборачиваемость, дней".)
            if canonical is None and file_type == "leftout_old":
                lower = normalize_header_lower(h)
                # Встречается и формат "Оборачиваемость, дней", и укороченный "Оборачиваемость".
                if "оборачиваемост" in lower:
                    canonical = "Оборачиваемость, дней"
                elif lower.startswith("среднесуточные продажи"):
                    # Two variants: regular and FBO/15 days.
                    if "fbo" in lower and "15" in lower:
                        canonical = "Среднесуточные продажи FBO за 15 дней, шт"
                    else:
                        canonical = "Среднесуточные продажи"
                elif lower.startswith("к отправке"):
                    canonical = "К отправке"
                elif lower.startswith("общий остаток"):
                    canonical = "Общий остаток"
                elif lower.startswith("название товара") or lower.startswith("наименование"):
                    canonical = "Наименование"
                elif lower.startswith("в продаже"):
                    canonical = "В продаже"
                elif "себест" in lower and "сум" in lower:
                    canonical = "Себест. (сумы)"
                elif "стоимость продажи" in lower and "сум" in lower:
                    canonical = "Стоимость продажи (сумы)"
                elif "стоимость хранения" in lower and ("1 дня" in lower or "1 день" in lower or "сут" in lower):
                    canonical = "Стоимость хранения 1 дня, сум"
                elif ("хранение" in lower or "хранения" in lower) and ("дн" in lower or "сут" in lower):
                    canonical = "Стоимость хранения 1 дня, сум"
                elif "штрихкод" in lower:
                    canonical = "Штрихкод"
                elif lower == "sku" or lower.endswith(" sku") or " sku" in lower:
                    canonical = "SKU"
                elif "id" in lower and "товар" in lower:
                    canonical = "ID товара"
                elif "ссылка" in lower and "товар" in lower:
                    canonical = "Ссылка на товар"
        if canonical:
            # Если несколько заголовков маппятся в одну каноническую колонку — берём первый
            # (например Sotuv qiymati (soʻm) и Sotuv qiymati (summa) (soʻm) → одна Стоимость продажи)
            if canonical not in assigned_canonical:
                rename[h] = canonical
                assigned_canonical.add(canonical)

    # Required check
    got_canonical = set(rename.values())
    missing = [c for c in required_canonical if c not in got_canonical]
    if missing:
        rev_uz: Dict[str, List[str]] = {}
        for uz_norm, ru in uz_map.items():
            if ru in missing:
                rev_uz.setdefault(ru, []).append(uz_norm)
        raise MissingRequiredColumnsError(
            missing, file_type,
            possible_uz=rev_uz,
            possible_ru=canonical_set,
            found_headers=normalized_headers,
        )

    lang = detect_language(file_type, normalized_headers)
    return rename, lang
