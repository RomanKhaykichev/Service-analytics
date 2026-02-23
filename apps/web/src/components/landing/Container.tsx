import { cn } from "@/lib/utils";

interface ContainerProps {
  children: React.ReactNode;
  className?: string;
}

/** Обёртка секции лендинга: центрирование и отступы по макету Figma. */
export function Container({ children, className }: ContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full max-w-[1400px] px-4 sm:px-6 md:px-8 lg:px-10",
        className
      )}
    >
      {children}
    </div>
  );
}
