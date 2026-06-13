import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { getProductImageSrc } from "@/lib/productImage";

interface ProductThumbnailProps {
  imageUrl: string | null | undefined;
  alt: string;
  className?: string;
  placeholderClassName?: string;
  fit?: "cover" | "contain";
  frame?: boolean;
}

export function ProductThumbnail({
  imageUrl,
  alt,
  className,
  placeholderClassName,
  fit = "cover",
  frame = true,
}: ProductThumbnailProps) {
  const [failed, setFailed] = useState(false);
  const [src, setSrc] = useState(() => getProductImageSrc(imageUrl));

  useEffect(() => {
    setFailed(false);
    setSrc(getProductImageSrc(imageUrl));
  }, [imageUrl]);

  const imgClassName = cn(
    "shrink-0",
    frame && "rounded-md border border-border bg-muted",
    fit === "contain" ? "object-contain" : "object-cover",
    className ?? "h-10 w-10",
  );
  const emptyClassName = cn(
    "shrink-0 rounded-md border-2 border-purple-500/35 bg-muted/30",
    placeholderClassName ?? className ?? "h-10 w-10",
  );

  if (!src || failed) {
    return <span className={emptyClassName} aria-hidden />;
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className={imgClassName}
    />
  );
}
