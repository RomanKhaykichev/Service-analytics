import privacy from "@/content/legal/privacy.json";
import { LegalDocumentView } from "@/components/legal/LegalDocumentView";

export default function Privacy() {
  return <LegalDocumentView blocks={privacy} />;
}
