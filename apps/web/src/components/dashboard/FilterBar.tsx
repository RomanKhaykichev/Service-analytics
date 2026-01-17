import { Calendar, Filter, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface FilterBarProps {
  onExport?: () => void;
}

export function FilterBar({ onExport }: FilterBarProps) {
  return (
    <div className="filter-bar animate-fade-in">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Filter className="w-4 h-4" />
        <span className="text-sm font-medium">Фильтры:</span>
      </div>

      <Select defaultValue="30days">
        <SelectTrigger className="w-40 bg-background">
          <Calendar className="w-4 h-4 mr-2" />
          <SelectValue placeholder="Период" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="7days">7 дней</SelectItem>
          <SelectItem value="30days">30 дней</SelectItem>
          <SelectItem value="90days">Квартал</SelectItem>
          <SelectItem value="year">Год</SelectItem>
          <SelectItem value="custom">Свой период</SelectItem>
        </SelectContent>
      </Select>

      <Select defaultValue="all">
        <SelectTrigger className="w-40 bg-background">
          <SelectValue placeholder="Категория" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все категории</SelectItem>
          <SelectItem value="electronics">Электроника</SelectItem>
          <SelectItem value="home">Дом и кухня</SelectItem>
          <SelectItem value="beauty">Красота</SelectItem>
          <SelectItem value="clothes">Одежда</SelectItem>
        </SelectContent>
      </Select>

      <Select defaultValue="all">
        <SelectTrigger className="w-36 bg-background">
          <SelectValue placeholder="Регион" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все регионы</SelectItem>
          <SelectItem value="tashkent">Ташкент</SelectItem>
          <SelectItem value="samarkand">Самарканд</SelectItem>
          <SelectItem value="bukhara">Бухара</SelectItem>
        </SelectContent>
      </Select>

      <div className="flex-1" />

      <Button variant="outline" size="sm" onClick={onExport}>
        <Download className="w-4 h-4 mr-2" />
        Экспорт
      </Button>
    </div>
  );
}
