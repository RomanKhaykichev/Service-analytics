import userAgreement from "@/content/legal/user-agreement.json";
import { LegalDocumentView } from "@/components/legal/LegalDocumentView";

export default function UserAgreement() {
  return <LegalDocumentView blocks={userAgreement} />;
}
