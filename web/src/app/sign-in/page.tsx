import { redirect } from "next/navigation";

/** Sign-in is removed for the demo phase. Old links land on the app. TODO(auth): restore before real data. */
export default function SignInPage() {
  redirect("/");
}
