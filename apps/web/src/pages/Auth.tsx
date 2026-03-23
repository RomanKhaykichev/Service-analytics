import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

export interface AuthFormContentProps {
  defaultTab?: 'signin' | 'signup';
  onSuccess: () => void;
  /** Класс для карточки (в диалоге — убрать рамку/тень). */
  cardClassName?: string;
}

/** Форма входа/регистрации без обёртки страницы. Используется на странице /auth и в модалке на лендинге. */
export function AuthFormContent({ defaultTab = 'signin', onSuccess, cardClassName }: AuthFormContentProps) {
  const { signIn, signUp, verifyPhone, resendPhoneOtp } = useAuth();
  const { language } = useLanguage();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [consentProcessing, setConsentProcessing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>(defaultTab);
  const [pendingVerify, setPendingVerify] = useState<{
    pendingId: string;
    phoneMasked: string;
  } | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [resendCooldown, setResendCooldown] = useState(0);
  useEffect(() => {
    setActiveTab(defaultTab);
  }, [defaultTab]);

  const validateEmail = (email: string) => {
    const trimmed = (email || '').trim();
    if (!trimmed) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    return emailRegex.test(trimmed);
  };

  const validatePassword = (password: string) => {
    return password.length >= 6;
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 9);
    setPhone(digits);
  };
  const phoneForSubmit = (): string | undefined =>
    phone.length === 9 ? `+998${phone}` : undefined;

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateEmail(email)) {
      toast.error(language === 'uz' ? 'To‘g‘ri email kiriting' : 'Введите корректный email');
      return;
    }

    if (!validatePassword(password)) {
      toast.error(
        language === 'uz'
          ? 'Parol kamida 6 ta belgidan iborat bo‘lishi kerak'
          : 'Пароль должен быть не менее 6 символов',
      );
      return;
    }

    setLoading(true);
    const { error } = await signIn(email.trim(), password);
    setLoading(false);

    if (error) {
      const msg = error.message || '';
      if (msg.includes('Invalid login credentials') || (msg.includes('Invalid') && msg.includes('password'))) {
        toast.error(language === 'uz' ? 'Email yoki parol noto‘g‘ri' : 'Неверный email или пароль');
      } else if (msg.includes('Phone not verified') || msg.includes('подтвержд')) {
        toast.error(
          language === 'uz'
            ? 'Avval ro‘yxatdan o‘tishda telefonni SMS orqali tasdiqlang'
            : 'Сначала подтвердите телефон по SMS при регистрации',
        );
      } else if (msg.includes('Email not confirmed')) {
        toast.error(
          language === 'uz'
            ? 'Kirishdan oldin emailingizni tasdiqlang'
            : 'Подтвердите email перед входом',
        );
      } else if (msg.includes('подключиться') || msg.includes('Failed to fetch')) {
        toast.error(
          language === 'uz'
            ? "API bilan ulanish imkoni bo'lmadi. Iltimos, apps/api papkasida serverni (8000-port) ishga tushiring va saytni npm run dev orqali oching."
            : 'Не удалось подключиться к API. Запустите сервер в папке apps/api (uvicorn на порту 8000) и откройте сайт через npm run dev.',
        );
      } else {
        toast.error(msg || (language === 'uz' ? 'Kirishda xatolik' : 'Ошибка входа'));
      }
      return;
    }

    toast.success(language === 'uz' ? 'Xush kelibsiz!' : 'Добро пожаловать!');
    onSuccess();
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!fullName.trim()) {
      toast.error(language === 'uz' ? 'Ismingizni kiriting' : 'Введите ваше имя');
      return;
    }

    if (!validateEmail(email)) {
      toast.error(language === 'uz' ? 'To‘g‘ri email kiriting' : 'Введите корректный email');
      return;
    }

    if (!validatePassword(password)) {
      toast.error(
        language === 'uz'
          ? 'Parol kamida 6 ta belgidan iborat bo‘lishi kerak'
          : 'Пароль должен быть не менее 6 символов',
      );
      return;
    }

    if (!consentProcessing) {
      toast.error(
        language === 'uz'
          ? 'Shaxsiy maʼlumotlarni qayta ishlashga rozilik berish kerak'
          : 'Необходимо дать согласие на обработку персональных данных',
      );
      return;
    }

    if (phone.length !== 9) {
      toast.error(
        language === 'uz'
          ? 'Telefon raqamini to‘liq kiriting (9 raqam)'
          : 'Введите номер телефона полностью (9 цифр)',
      );
      return;
    }

    setLoading(true);
    const { error, pending } = await signUp(email.trim(), password, fullName.trim(), phoneForSubmit(), consentProcessing);
    setLoading(false);

    if (pending?.next === 'verify_phone') {
      setPendingVerify({
        pendingId: pending.pending_id,
        phoneMasked: pending.phone_masked,
      });
      setOtpCode('');
      setResendCooldown(60);
      toast.success(
        language === 'uz'
          ? 'SMS-kod telefoningizga yuborildi'
          : 'Код подтверждения отправлен по SMS',
      );
      return;
    }

    if (error) {
      const msg = (error.message || '').trim();
      if (msg.includes('already exists') || msg.includes('already registered')) {
        if (msg.toLowerCase().includes('phone')) {
          toast.error(
            language === 'uz'
              ? 'Bu telefon raqami bilan foydalanuvchi allaqachon ro‘yxatdan o‘tgan'
              : 'Пользователь с таким номером телефона уже зарегистрирован',
          );
        } else {
          toast.error(
            language === 'uz'
              ? 'Bu email bilan foydalanuvchi allaqachon ro‘yxatdan o‘tgan'
              : 'Пользователь с таким email уже зарегистрирован',
          );
        }
      } else if (msg.includes('Consent') || msg.includes('consent')) {
        toast.error(
          language === 'uz'
            ? 'Shaxsiy maʼlumotlarni qayta ishlashga rozilik berish kerak'
            : 'Необходимо дать согласие на обработку персональных данных',
        );
      } else if (msg.includes('valid email') || msg.includes('Invalid email') || /validation|email.*format/i.test(msg)) {
        toast.error(language === 'uz' ? 'To‘g‘ri email kiriting' : 'Введите корректный email');
      } else if (msg.includes('подключиться к серверу') || msg.includes('Failed to fetch')) {
        toast.error(
          language === 'uz'
            ? "API bilan ulanish imkoni bo'lmadi. Iltimos, serverni (apps/api) ishga tushiring va sahifani qayta yuklang."
            : 'Не удалось подключиться к API. Запустите сервер (apps/api) и обновите страницу.',
        );
      } else {
        toast.error(
          msg || (language === 'uz' ? 'Ro‘yxatdan o‘tishda xatolik' : 'Ошибка регистрации'),
        );
      }
      return;
    }

    if (!error) {
      toast.error(language === 'uz' ? 'Kutilmagan javob' : 'Неожиданный ответ сервера');
    }
  };

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setInterval(() => setResendCooldown((c) => (c <= 1 ? 0 : c - 1)), 1000);
    return () => clearInterval(t);
  }, [resendCooldown]);

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingVerify) return;
    const code = otpCode.replace(/\D/g, '').slice(0, 6);
    if (code.length !== 6) {
      toast.error(language === 'uz' ? '6 raqamli kodni kiriting' : 'Введите 6-значный код');
      return;
    }
    setLoading(true);
    const { error } = await verifyPhone(pendingVerify.pendingId, code);
    setLoading(false);
    if (error) {
      toast.error(error.message || (language === 'uz' ? 'Kod noto‘g‘ri' : 'Неверный код'));
      return;
    }
    toast.success(language === 'uz' ? 'Telefon tasdiqlandi!' : 'Телефон подтверждён!');
    setPendingVerify(null);
    onSuccess();
  };

  const handleResendOtp = async () => {
    if (!pendingVerify || resendCooldown > 0 || loading) return;
    setLoading(true);
    const { error } = await resendPhoneOtp(pendingVerify.pendingId);
    setLoading(false);
    if (error) {
      if (error.message.includes('429') || error.message.toLowerCase().includes('too many')) {
        toast.error(language === 'uz' ? 'Juda ko‘p so‘rov. Keyinroq urinib ko‘ring.' : 'Слишком много запросов. Попробуйте позже.');
      } else {
        toast.error(error.message);
      }
      return;
    }
    setResendCooldown(60);
    toast.success(language === 'uz' ? 'Kod qayta yuborildi' : 'Код отправлен повторно');
  };

  if (pendingVerify) {
    return (
      <Card className={cn('w-full max-w-md', cardClassName)}>
        <CardHeader className="text-center pb-2">
          <CardTitle className="text-xl">
            {language === 'uz' ? 'Telefonni tasdiqlang' : 'Подтвердите телефон'}
          </CardTitle>
          <CardDescription>
            {language === 'uz' ? 'Kod yuborildi: ' : 'Код отправлен на '}
            {pendingVerify.phoneMasked}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleVerifyOtp} className="space-y-4">
            <Input
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              maxLength={6}
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              disabled={loading}
              className="text-center text-2xl tracking-[0.5em] font-mono"
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {language === 'uz' ? 'Tekshirilmoqda...' : 'Проверка...'}
                </>
              ) : (
                (language === 'uz' ? 'Tasdiqlash' : 'Подтвердить')
              )}
            </Button>
            <Button type="button" variant="outline" className="w-full" disabled={loading || resendCooldown > 0} onClick={handleResendOtp}>
              {resendCooldown > 0
                ? (language === 'uz' ? `Qayta yuborish (${resendCooldown}s)` : `Отправить снова (${resendCooldown}s)`)
                : (language === 'uz' ? 'Kodni qayta yuborish' : 'Отправить код повторно')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => {
                setPendingVerify(null);
                setOtpCode('');
              }}
            >
              {language === 'uz' ? 'Orqaga' : 'Назад'}
            </Button>
          </form>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('w-full max-w-md', cardClassName)}>
      <CardHeader className="text-center pb-2">
        {activeTab === 'signin' && (
          <div className="flex justify-center mb-0.5">
            <img src="/favicon.png" alt="" className="h-12 w-12 object-contain" />
          </div>
        )}
        <CardTitle className="text-2xl font-normal">
          <span className="font-bold">PROFi</span>
          <span className="font-normal">board</span>
        </CardTitle>
        <CardDescription>
          {language === 'uz'
            ? 'Marketpleys sotuvchilari uchun analitik servis'
            : 'Аналитический сервис для продавцов маркетплейса'}
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-0">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'signin' | 'signup')} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="signin">
              {language === 'uz' ? 'Kirish' : 'Вход'}
            </TabsTrigger>
            <TabsTrigger value="signup">
              {language === 'uz' ? "Ro'yxatdan o'tish" : 'Регистрация'}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="signin">
            <form onSubmit={handleSignIn} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="signin-email">Email</Label>
                <Input
                  id="signin-email"
                  type="email"
                  placeholder="example@mail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="signin-password">
                  {language === 'uz' ? 'Parol' : 'Пароль'}
                </Label>
                <div className="relative">
                  <Input
                    id="signin-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {language === 'uz' ? 'Kirish...' : 'Вход...'}
                  </>
                ) : (
                  (language === 'uz' ? 'Kirish' : 'Войти')
                )}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="signup">
            <form onSubmit={handleSignUp} className="space-y-4 mt-4">
              <Input
                id="signup-name"
                type="text"
                placeholder={language === 'uz' ? 'Ism Familiya' : 'Имя Фамилия'}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={loading}
              />

              <Input
                id="signup-email"
                type="email"
                placeholder={
                  language === 'uz'
                    ? 'Sizning emailingiz (example@mail.com)'
                    : 'Ваша почта (example@mail.com)'
                }
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />

              <div className="flex rounded-md border border-input bg-background ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 has-[:disabled]:opacity-50 has-[:disabled]:cursor-not-allowed">
                <span className="inline-flex items-center px-3 text-muted-foreground border-r border-input bg-muted/50 text-sm shrink-0">
                  +998
                </span>
                <Input
                  id="signup-phone"
                  type="tel"
                  placeholder="90 123 45 67"
                  value={phone}
                  onChange={handlePhoneChange}
                  disabled={loading}
                  maxLength={9}
                  inputMode="numeric"
                  autoComplete="tel"
                  className="border-0 rounded-none focus-visible:ring-0 focus-visible:ring-offset-0 pl-2"
                />
              </div>

              <div className="relative">
                <Input
                  id="signup-password"
                  type={showPassword ? 'text' : 'password'}
                placeholder={
                  language === 'uz'
                    ? 'Parol (kamida 6 ta belgi)'
                    : 'Пароль (минимум 6 символов)'
                }
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>

              <div className="flex items-start gap-3 rounded-md border border-border p-3">
                <Checkbox
                  id="signup-consent"
                  checked={consentProcessing}
                  onCheckedChange={(checked) => setConsentProcessing(checked === true)}
                  disabled={loading}
                  className="mt-0.5"
                />
                <label
                  htmlFor="signup-consent"
                  className="text-xs text-muted-foreground leading-snug cursor-pointer"
                >
                  {language === 'uz'
                    ? "«Ro'yxatdan o'tish» tugmasini bosish orqali siz shaxsiy maʼlumotlaringizni qayta ishlashga rozilik bildirasiz va "
                    : 'Нажимая на кнопку «Зарегистрироваться», Вы даете согласие на обработку своих персональных данных и соглашаетесь с '}
                  <a
                    href="/privacy"
                    className="text-primary underline underline-offset-2 hover:opacity-90"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {language === 'uz'
                      ? 'maxfiylik siyosati'
                      : 'политикой конфиденциальности'}
                  </a>
                  {' '}
                  {language === 'uz' ? 'va ' : 'и '}
                  <a
                    href="/offer"
                    className="text-primary underline underline-offset-2 hover:opacity-90"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {language === 'uz' ? 'oferta shartnomasi' : 'договором оферты'}
                  </a>
                  .
                </label>
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {language === 'uz' ? "Ro'yxatdan o'tish..." : 'Регистрация...'}
                  </>
                ) : (
                  (language === 'uz' ? "Ro'yxatdan o'tish" : 'Зарегистрироваться')
                )}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

/** Модальное окно входа/регистрации поверх лендинга. */
export function AuthDialog({
  open,
  onOpenChange,
  defaultTab = 'signin',
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: 'signin' | 'signup';
}) {
  const navigate = useNavigate();

  const handleSuccess = () => {
    onOpenChange(false);
    navigate('/');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md w-[calc(100vw-2rem)] sm:w-full overflow-hidden"
        // Registration OTP flow must be closed only via explicit "X" button.
        onPointerDownOutside={(event) => event.preventDefault()}
        onInteractOutside={(event) => event.preventDefault()}
      >
        <AuthFormContent key={defaultTab} defaultTab={defaultTab} onSuccess={handleSuccess} cardClassName="border-0 shadow-none w-full max-w-none" />
      </DialogContent>
    </Dialog>
  );
}

export default function Auth() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const defaultTab = searchParams.get('tab') === 'signup' ? 'signup' : 'signin';

  // Redirect if already authenticated
  useEffect(() => {
    if (user) {
      navigate('/');
    }
  }, [user, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <AuthFormContent defaultTab={defaultTab} onSuccess={() => navigate('/')} />
    </div>
  );
}
