const tg = window.Telegram?.WebApp;

export const initTelegram = () => {
  tg?.ready();
  tg?.expand();
};

export const getUser = () =>
  tg?.initDataUnsafe?.user || { id: 12345, first_name: 'Test', username: 'test' };

export const getInitData = () => tg?.initData || 'test_init_data';

export const getThemeParams = () => tg?.themeParams || {};
