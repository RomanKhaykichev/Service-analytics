import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type Language = 'ru' | 'uz';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const translations: Record<Language, Record<string, string>> = {
  ru: {
    // Navigation
    'nav.dashboard': 'Дашборд',
    'nav.products': 'Товары',
    'nav.analytics': 'Аналитика',
    'nav.competitors': 'Конкуренты',
    'nav.trends': 'Тренды',
    'nav.reports': 'Отчёты',
    'nav.support': 'Поддержка',
    
    // Tabs
    'tabs.summary': 'Сводка',
    'tabs.products': 'Товары',
    'tabs.daily': 'По дням',
    'tabs.expenses': 'Расходы',
    'tabs.shipment': 'Поставка',
    
    // Filters
    'filter.today': 'Сегодня',
    'filter.yesterday': 'Вчера',
    'filter.week': 'Неделя',
    'filter.month': 'Месяц',
    'filter.year': 'Год',
    'filter.period': 'Период',
    'filter.all': 'Все',
    'filter.excess': 'Избыток',
    'filter.outOfStock': 'Нет на складе',
    'filter.needSupply': 'Нужна поставка',
    
    // KPI Cards
    'kpi.revenue': 'Выручка',
    'kpi.orders': 'Заказы',
    'kpi.returns': 'Возвраты',
    'kpi.profit': 'Прибыль',
    'kpi.marginality': 'Маржинальность',
    'kpi.averageCheck': 'Средний чек',
    
    // Blocks
    'block.finances': 'Финансы',
    'block.expenses': 'Расходы',
    'block.warehouse': 'Склад',
    'block.revenueProgress': 'Накопительная выручка',
    
    // Finance items
    'finance.revenue': 'Выручка',
    'finance.logistics': 'Логистика',
    'finance.commission': 'Комиссия',
    'finance.promoDiscount': 'Скидка по акции',
    'finance.netRevenue': 'Чистая выручка',
    
    // Expense items
    'expense.soldGoodsCost': 'Себест. проданных товаров',
    'expense.logistics': 'Логистика',
    'expense.commission': 'Комиссия',
    'expense.promoDiscount': 'Скидка по акции',
    'expense.advertising': 'Реклама',
    'expense.fines': 'Штрафы',
    'expense.storage': 'Хранение',
    'expense.other': 'Прочее',
    'expense.total': 'Итого расходов',
    
    // Warehouse items
    'warehouse.warehouseStock': 'Себест. товара на складе',
    'warehouse.potentialRevenue': 'Потенциальная выручка',
    'warehouse.potentialProfit': 'Потенциальная прибыль',
    
    // Table headers
    'table.product': 'Товар',
    'table.article': 'Артикул',
    'table.category': 'Категория',
    'table.costPrice': 'Себестоимость',
    'table.price': 'Цена',
    'table.orders': 'Заказы',
    'table.returns': 'Возвраты',
    'table.stock': 'Остаток',
    'table.availability': 'Наличие',
    'table.revenue': 'Выручка',
    'table.profit': 'Прибыль',
    'table.margin': 'Маржа',
    
    // Availability status
    'availability.excess': 'Избыток',
    'availability.outOfStock': 'Нет на складе',
    'availability.needSupply': 'Нужна поставка',
    
    // Header
    'header.search': 'Поиск товаров, категорий...',
    'header.notifications': 'Уведомления',
    'header.allNotifications': 'Все уведомления',
    'header.help': 'Помощь',
    'header.faq': 'Часто задаваемые вопросы',
    'header.videoTutorials': 'Видео-уроки',
    'header.support': 'Поддержка',
    'header.myAccount': 'Мой аккаунт',
    'header.profile': 'Профиль',
    'header.tariff': 'Тариф',
    'header.extendTariff': 'Продлить тариф',
    'header.language': 'Язык',
    'header.logout': 'Выйти',
    
    // Profile dialog
    'profile.title': 'Профиль',
    'profile.accountData': 'Данные аккаунта',
    'profile.name': 'Имя',
    'profile.email': 'Email',
    'profile.phone': 'Номер телефона',
    'profile.save': 'Сохранить',
    'profile.tariffPlan': 'Тарифный план',
    'profile.active': 'Активен',
    'profile.validUntil': 'Действует до',
    'profile.daysRemaining': 'Осталось дней',
    
    // Language dialog
    'language.title': 'Выбор языка',
    'language.russian': 'Русский',
    'language.uzbek': 'Узбекский',
    
    // Report upload
    'report.uploadReports': 'Загрузить отчёты',
    'report.sales': 'Продажи',
    'report.expenses': 'Расходы',
    'report.inventory': 'Остатки',
    'report.storage': 'Хранение',
    
    // Actions
    'action.export': 'Экспорт',
    'action.import': 'Импорт',
    'action.apply': 'Применить',
    'action.cancel': 'Отмена',
    'action.close': 'Закрыть',
    
    // Common
    'common.from': 'от',
    'common.to': 'до',
    'common.total': 'Итого',
    'common.pieces': 'шт',
    'common.sum': 'сум',
  },
  uz: {
    // Navigation
    'nav.dashboard': 'Boshqaruv paneli',
    'nav.products': 'Mahsulotlar',
    'nav.analytics': 'Tahlil',
    'nav.competitors': 'Raqobatchilar',
    'nav.trends': 'Trendlar',
    'nav.reports': 'Hisobotlar',
    'nav.support': 'Yordam',
    
    // Tabs
    'tabs.summary': 'Xulosa',
    'tabs.products': 'Mahsulotlar',
    'tabs.daily': 'Kunlik',
    'tabs.expenses': 'Xarajatlar',
    'tabs.shipment': 'Yetkazib berish',
    
    // Filters
    'filter.today': 'Bugun',
    'filter.yesterday': 'Kecha',
    'filter.week': 'Hafta',
    'filter.month': 'Oy',
    'filter.year': 'Yil',
    'filter.period': 'Davr',
    'filter.all': 'Hammasi',
    'filter.excess': 'Ortiqcha',
    'filter.outOfStock': 'Omborda yo\'q',
    'filter.needSupply': 'Yetkazish kerak',
    
    // KPI Cards
    'kpi.revenue': 'Daromad',
    'kpi.orders': 'Buyurtmalar',
    'kpi.returns': 'Qaytarishlar',
    'kpi.profit': 'Foyda',
    'kpi.marginality': 'Marjinallik',
    'kpi.averageCheck': "O'rtacha chek",
    
    // Blocks
    'block.finances': 'Moliya',
    'block.expenses': 'Xarajatlar',
    'block.warehouse': 'Ombor',
    'block.revenueProgress': "Jami daromad",
    
    // Finance items
    'finance.revenue': 'Daromad',
    'finance.logistics': 'Logistika',
    'finance.commission': 'Komissiya',
    'finance.promoDiscount': 'Aksiya chegirmasi',
    'finance.netRevenue': 'Sof daromad',
    
    // Expense items
    'expense.soldGoodsCost': "Sotilgan tovarlar tannarxi",
    'expense.logistics': 'Logistika',
    'expense.commission': 'Komissiya',
    'expense.promoDiscount': 'Aksiya chegirmasi',
    'expense.advertising': 'Reklama',
    'expense.fines': 'Jarimalar',
    'expense.storage': 'Saqlash',
    'expense.other': 'Boshqa',
    'expense.total': 'Jami xarajatlar',
    
    // Warehouse items
    'warehouse.warehouseStock': "Ombordagi tovar tannarxi",
    'warehouse.potentialRevenue': 'Potentsial daromad',
    'warehouse.potentialProfit': 'Potentsial foyda',
    
    // Table headers
    'table.product': 'Mahsulot',
    'table.article': 'Artikul',
    'table.category': 'Kategoriya',
    'table.costPrice': 'Tannarx',
    'table.price': 'Narx',
    'table.orders': 'Buyurtmalar',
    'table.returns': 'Qaytarishlar',
    'table.stock': 'Qoldiq',
    'table.availability': 'Mavjudlik',
    'table.revenue': 'Daromad',
    'table.profit': 'Foyda',
    'table.margin': 'Marja',
    
    // Availability status
    'availability.excess': 'Ortiqcha',
    'availability.outOfStock': "Omborda yo'q",
    'availability.needSupply': 'Yetkazish kerak',
    
    // Header
    'header.search': "Mahsulot, kategoriya qidirish...",
    'header.notifications': 'Bildirishnomalar',
    'header.allNotifications': 'Barcha bildirishnomalar',
    'header.help': 'Yordam',
    'header.faq': "Ko'p so'raladigan savollar",
    'header.videoTutorials': 'Video darsliklar',
    'header.support': "Qo'llab-quvvatlash",
    'header.myAccount': 'Mening hisobim',
    'header.profile': 'Profil',
    'header.tariff': 'Tarif',
    'header.extendTariff': 'Tarifni uzaytirish',
    'header.language': 'Til',
    'header.logout': 'Chiqish',
    
    // Profile dialog
    'profile.title': 'Profil',
    'profile.accountData': "Hisob ma'lumotlari",
    'profile.name': 'Ism',
    'profile.email': 'Email',
    'profile.phone': 'Telefon raqami',
    'profile.save': 'Saqlash',
    'profile.tariffPlan': 'Tarif rejasi',
    'profile.active': 'Faol',
    'profile.validUntil': 'Amal qilish muddati',
    'profile.daysRemaining': 'Qolgan kunlar',
    
    // Language dialog
    'language.title': 'Tilni tanlash',
    'language.russian': 'Ruscha',
    'language.uzbek': "O'zbekcha",
    
    // Report upload
    'report.uploadReports': 'Hisobotlarni yuklash',
    'report.sales': 'Sotuvlar',
    'report.expenses': 'Xarajatlar',
    'report.inventory': 'Qoldiqlar',
    'report.storage': 'Saqlash',
    
    // Actions
    'action.export': 'Eksport',
    'action.import': 'Import',
    'action.apply': "Qo'llash",
    'action.cancel': 'Bekor qilish',
    'action.close': 'Yopish',
    
    // Common
    'common.from': 'dan',
    'common.to': 'gacha',
    'common.total': 'Jami',
    'common.pieces': 'dona',
    'common.sum': "so'm",
  },
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('app-language');
    return (saved as Language) || 'ru';
  });

  useEffect(() => {
    localStorage.setItem('app-language', language);
  }, [language]);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
  };

  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
