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

export interface AuthFormContentProps {
  defaultTab?: 'signin' | 'signup';
  onSuccess: () => void;
  /** Класс для карточки (в диалоге — убрать рамку/тень). */
  cardClassName?: string;
}

/** Форма входа/регистрации без обёртки страницы. Используется на странице /auth и в модалке на лендинге. */
export function AuthFormContent({ defaultTab = 'signin', onSuccess, cardClassName }: AuthFormContentProps) {
  const { signIn, signUp } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [consentProcessing, setConsentProcessing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>(defaultTab);
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

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateEmail(email)) {
      toast.error('Введите корректный email');
      return;
    }

    if (!validatePassword(password)) {
      toast.error('Пароль должен быть не менее 6 символов');
      return;
    }

    setLoading(true);
    const { error } = await signIn(email.trim(), password);
    setLoading(false);

    if (error) {
      const msg = error.message || '';
      if (msg.includes('Invalid login credentials') || (msg.includes('Invalid') && msg.includes('password'))) {
        toast.error('Неверный email или пароль');
      } else if (msg.includes('Email not confirmed')) {
        toast.error('Подтвердите email перед входом');
      } else if (msg.includes('подключиться') || msg.includes('Failed to fetch')) {
        toast.error('Не удалось подключиться к API. Запустите сервер в папке apps/api (uvicorn на порту 8000) и откройте сайт через npm run dev.');
      } else {
        toast.error(msg || 'Ошибка входа');
      }
      return;
    }

    toast.success('Добро пожаловать!');
    onSuccess();
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!fullName.trim()) {
      toast.error('Введите ваше имя');
      return;
    }

    if (!validateEmail(email)) {
      toast.error('Введите корректный email');
      return;
    }

    if (!validatePassword(password)) {
      toast.error('Пароль должен быть не менее 6 символов');
      return;
    }

    if (!consentProcessing) {
      toast.error('Необходимо дать согласие на обработку персональных данных');
      return;
    }

    setLoading(true);
    const { error } = await signUp(email.trim(), password, fullName.trim(), (phone && phone.trim()) || undefined, consentProcessing);
    setLoading(false);

    if (error) {
      const msg = (error.message || '').trim();
      if (msg.includes('already exists') || msg.includes('already registered')) {
        if (msg.toLowerCase().includes('phone')) {
          toast.error('Пользователь с таким номером телефона уже зарегистрирован');
        } else {
          toast.error('Пользователь с таким email уже зарегистрирован');
        }
      } else if (msg.includes('Consent') || msg.includes('consent')) {
        toast.error('Необходимо дать согласие на обработку персональных данных');
      } else if (msg.includes('valid email') || msg.includes('Invalid email') || /validation|email.*format/i.test(msg)) {
        toast.error('Введите корректный email');
      } else if (msg.includes('подключиться к серверу') || msg.includes('Failed to fetch')) {
        toast.error('Не удалось подключиться к API. Запустите сервер (apps/api) и обновите страницу.');
      } else {
        toast.error(msg || 'Ошибка регистрации');
      }
      return;
    }

    toast.success('Регистрация успешна! Добро пожаловать!');
    onSuccess();
  };

  return (
    <Card className={cn('w-full max-w-md', cardClassName)}>
      <CardHeader className="text-center pb-2">
        {activeTab === 'signin' && (
          <div className="flex justify-center mb-0.5">
            <img src="/favicon.png" alt="" className="h-12 w-12 object-contain" />
          </div>
        )}
        <CardTitle className="text-2xl font-normal"><span className="font-bold">PROFi</span><span className="font-normal">board</span></CardTitle>
        <CardDescription>
          Аналитический сервис для продавцов маркетплейса
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-0">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'signin' | 'signup')} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="signin">Вход</TabsTrigger>
            <TabsTrigger value="signup">Регистрация</TabsTrigger>
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
                <Label htmlFor="signin-password">Пароль</Label>
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
                    Вход...
                  </>
                ) : (
                  'Войти'
                )}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="signup">
            <form onSubmit={handleSignUp} className="space-y-4 mt-4">
              <Input
                id="signup-name"
                type="text"
                placeholder="Имя Фамилия"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={loading}
              />

              <Input
                id="signup-email"
                type="email"
                placeholder="Ваша почта (example@mail.com)"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />

              <Input
                id="signup-phone"
                type="tel"
                placeholder="+998 90 123 45 67"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={loading}
              />

              <div className="relative">
                <Input
                  id="signup-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Пароль (минимум 6 символов)"
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
                <label htmlFor="signup-consent" className="text-xs text-muted-foreground leading-snug cursor-pointer">
                  Нажимая на кнопку «Зарегистрироваться», Вы даете согласие на обработку своих персональных данных и соглашаетесь с{' '}
                  <a href="/privacy" className="text-primary underline underline-offset-2 hover:opacity-90" target="_blank" rel="noopener noreferrer">
                    политикой конфиденциальности
                  </a>
                  {' '}и{' '}
                  <a href="/offer" className="text-primary underline underline-offset-2 hover:opacity-90" target="_blank" rel="noopener noreferrer">
                    договором оферты
                  </a>
                  .
                </label>
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Регистрация...
                  </>
                ) : (
                  'Зарегистрироваться'
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
      <DialogContent className="max-w-md w-[calc(100vw-2rem)] sm:w-full overflow-hidden" hideCloseButton>
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
