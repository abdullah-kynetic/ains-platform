"use client";
import { AuthGate } from "@/components/auth/session";
export default function ReportsLayout({children}:{children:React.ReactNode}) {return <AuthGate role="auditor">{children}</AuthGate>;}
