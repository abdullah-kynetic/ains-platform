import { delay, readStore, updateStore } from "../mock/store";
import { seedNotifications } from "../mock/seed";
import type { Notification } from "./types";

const key = "kien-mock-notifications-v1";
// TODO(backend): GET /auditor/notifications -> Notification[] (newest first)
export const listNotifications = () => delay(readStore(key, seedNotifications));
// TODO(backend): POST /auditor/notifications/{id}/read
export const markRead = (id: string) => delay(updateStore(key, seedNotifications, (n) => { const x = n.find((i) => i.id === id); if (x) x.read = true; }));
// TODO(backend): POST /auditor/notifications/read-all
export const markAllRead = () => delay(updateStore(key, seedNotifications, (n) => n.map((i) => ({ ...i, read: true }))));
export const unreadCount = (list: Notification[]) => list.filter((n) => !n.read).length;
