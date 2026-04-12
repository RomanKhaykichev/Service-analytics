import offer from "@/content/legal/offer.json";
import { LegalDocumentView } from "@/components/legal/LegalDocumentView";

export default function Offer() {
  return <LegalDocumentView blocks={offer} />;
}
