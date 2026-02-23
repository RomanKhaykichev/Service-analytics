import { cn } from "@/lib/utils";

interface RevenueTrendIconProps {
  trend: "up" | "down";
  className?: string;
}

/**
 * Иконка тренда выручки: треугольник как у фавикона.
 * Положительный тренд — зелёный треугольник вверх, отрицательный — перевёрнутый, зелёный заменён на красный.
 */
export function RevenueTrendIcon({ trend, className }: RevenueTrendIconProps) {
  const isUp = trend === "up";
  const fill = isUp ? "#39ff14" : "#ef4444"; // зелёный / красный
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("w-4 h-4 shrink-0", !isUp && "rotate-180", className)}
      role="presentation"
      aria-hidden
    >
      {/* Скруглённый треугольник: вверх — зелёный, вниз — тот же, но компонент перевернём через rotate-180 */}
      <path
        d="M12 4L20 18H4L12 4Z"
        fill={fill}
        stroke="#1f2937"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}
