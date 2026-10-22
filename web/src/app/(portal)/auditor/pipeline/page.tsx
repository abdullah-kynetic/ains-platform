import { AuthGate } from "@/components/auth/session";
import { AuditorPipelineBoard } from "@/components/auditor/pipeline-board";

export default function AuditorPipelinePage() {
  return (
    <AuthGate role="auditor">
      <AuditorPipelineBoard />
    </AuthGate>
  );
}
