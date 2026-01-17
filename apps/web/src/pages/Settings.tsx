import { User, Link2, Bell, Palette, Shield, Key } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

const Settings = () => {
  return (
    <MainLayout>
      <Breadcrumb items={[{ label: "Настройки" }]} />

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Настройки</h1>
        <p className="text-muted-foreground">
          Управление аккаунтом и настройками платформы
        </p>
      </div>

      <Tabs defaultValue="account" className="space-y-6">
        <TabsList className="bg-muted/50">
          <TabsTrigger value="account" className="gap-2">
            <User className="w-4 h-4" />
            Аккаунт
          </TabsTrigger>
          <TabsTrigger value="integrations" className="gap-2">
            <Link2 className="w-4 h-4" />
            Интеграции
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-2">
            <Bell className="w-4 h-4" />
            Уведомления
          </TabsTrigger>
          <TabsTrigger value="branding" className="gap-2">
            <Palette className="w-4 h-4" />
            Брендинг
          </TabsTrigger>
        </TabsList>

        {/* Account Tab */}
        <TabsContent value="account">
          <div className="chart-container space-y-6">
            <div>
              <h3 className="font-semibold text-foreground mb-4">Профиль</h3>
              <div className="flex items-center gap-4 mb-6">
                <Avatar className="w-16 h-16">
                  <AvatarImage src="" />
                  <AvatarFallback className="bg-primary text-primary-foreground text-xl">
                    АН
                  </AvatarFallback>
                </Avatar>
                <div>
                  <Button variant="outline" size="sm">
                    Загрузить фото
                  </Button>
                  <p className="text-xs text-muted-foreground mt-1">
                    JPG, PNG до 5MB
                  </p>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Имя</Label>
                  <Input id="name" defaultValue="Александр Ниязов" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" defaultValue="admin@uzum.uz" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Телефон</Label>
                  <Input id="phone" defaultValue="+998 90 123 45 67" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">Роль</Label>
                  <Select defaultValue="owner">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="owner">Владелец</SelectItem>
                      <SelectItem value="analyst">Аналитик</SelectItem>
                      <SelectItem value="manager">Менеджер</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Безопасность
              </h3>
              <div className="space-y-4">
                <Button variant="outline">
                  <Key className="w-4 h-4 mr-2" />
                  Сменить пароль
                </Button>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">
                      Двухфакторная аутентификация
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Дополнительная защита аккаунта
                    </p>
                  </div>
                  <Switch />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <Button variant="outline">Отмена</Button>
              <Button>Сохранить</Button>
            </div>
          </div>
        </TabsContent>

        {/* Integrations Tab */}
        <TabsContent value="integrations">
          <div className="chart-container space-y-6">
            <div>
              <h3 className="font-semibold text-foreground mb-4">UZUM API</h3>
              <div className="p-4 rounded-lg border border-border bg-muted/30">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center">
                      <Link2 className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium text-foreground">UZUM Marketplace</p>
                      <p className="text-sm text-muted-foreground">Подключено</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm">
                    Настроить
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="api-key">API Ключ</Label>
                  <Input
                    id="api-key"
                    type="password"
                    defaultValue="uzum_api_xxxxxxxxxxxxxxxx"
                  />
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="font-semibold text-foreground mb-4">Вебхуки</h3>
              <div className="space-y-2">
                <Label htmlFor="webhook">URL вебхука</Label>
                <Input
                  id="webhook"
                  placeholder="https://your-server.com/webhook"
                />
                <p className="text-xs text-muted-foreground">
                  Получайте уведомления о событиях в реальном времени
                </p>
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="font-semibold text-foreground mb-4">Email отчёты</h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">
                    Автоматическая отправка отчётов
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Еженедельные отчёты на email
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <div className="chart-container space-y-6">
            <div>
              <h3 className="font-semibold text-foreground mb-4">Пороги уведомлений</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Изменение цен конкурентов</p>
                    <p className="text-sm text-muted-foreground">Порог: ±5%</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Падение конверсии</p>
                    <p className="text-sm text-muted-foreground">Порог: -10%</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Низкие запасы</p>
                    <p className="text-sm text-muted-foreground">Менее 50 единиц</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Негативные отзывы</p>
                    <p className="text-sm text-muted-foreground">Рейтинг ниже 4.0</p>
                  </div>
                  <Switch />
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="font-semibold text-foreground mb-4">Каналы уведомлений</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Email</p>
                    <p className="text-sm text-muted-foreground">admin@uzum.uz</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Внутренние уведомления</p>
                    <p className="text-sm text-muted-foreground">В интерфейсе платформы</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Branding Tab */}
        <TabsContent value="branding">
          <div className="chart-container space-y-6">
            <div>
              <h3 className="font-semibold text-foreground mb-4">Логотип компании</h3>
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
                  ЛОГО
                </div>
                <div>
                  <Button variant="outline" size="sm">
                    Загрузить логотип
                  </Button>
                  <p className="text-xs text-muted-foreground mt-1">
                    SVG, PNG до 2MB. Рекомендуется 200x200px
                  </p>
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="font-semibold text-foreground mb-4">Цвет акцента</h3>
              <div className="flex items-center gap-4">
                <div className="flex gap-2">
                  <button className="w-8 h-8 rounded-full bg-primary ring-2 ring-offset-2 ring-primary" />
                  <button className="w-8 h-8 rounded-full bg-accent" />
                  <button className="w-8 h-8 rounded-full bg-success" />
                  <button className="w-8 h-8 rounded-full bg-warning" />
                  <button className="w-8 h-8 rounded-full bg-destructive" />
                </div>
                <Input
                  className="w-28"
                  defaultValue="#6A0DAD"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <Button variant="outline">Отмена</Button>
              <Button>Сохранить</Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
};

export default Settings;
