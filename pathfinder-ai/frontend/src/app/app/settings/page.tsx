"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, RotateCcw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Card, Input, Label } from "@/components/ui/primitives";
import { PageHeader, SectionTitle } from "@/components/ui/states";
import { ApiError, api, get, patch, post } from "@/lib/api";
import { useAdjustRoadmap, useProfile } from "@/lib/queries";

export default function SettingsPage() {
  const profile = useProfile();
  const qc = useQueryClient();
  const router = useRouter();
  const adjust = useAdjustRoadmap();
  const status = useQuery({ queryKey: ["system"], queryFn: () => get<any>("/system/status") });
  const [name, setName] = useState("");
  const [hours, setHours] = useState(8);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  useEffect(() => {
    if (profile.data) { setName(profile.data.user.name); setHours(profile.data.hours_per_week); }
  }, [profile.data]);

  const save = async () => {
    try {
      await patch("/profile", { name, hours_per_week: hours });
      if (hours !== profile.data?.hours_per_week) await adjust.mutateAsync({ hours_per_week: hours }).catch(() => {});
      qc.invalidateQueries();
      toast.success("Saved.");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't save."); }
  };

  const exportData = async () => {
    const data = await get("/account/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url; a.download = "pathfinder-export.json"; a.click();
    URL.revokeObjectURL(url);
  };

  const deleteAccount = async () => {
    try {
      await api("/account", { method: "DELETE" });
      qc.clear();
      router.replace("/");
    } catch (e) { toast.error(e instanceof ApiError ? e.message : "Couldn't delete account."); }
  };

  const resetDemo = async () => {
    await post("/auth/demo/reset");
    qc.clear();
    toast.success("Demo profile restored.");
    router.replace("/app");
  };

  const isDemo = profile.data?.user.is_demo;

  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="Settings" title="Settings" />
      <section>
        <SectionTitle>Profile</SectionTitle>
        <Card className="space-y-5 p-6">
          <div><Label htmlFor="s-name">Name</Label><Input id="s-name" value={name} onChange={(e) => setName(e.target.value)} /></div>
          <div>
            <Label htmlFor="s-h">Hours per week for learning</Label>
            <div className="flex items-center gap-4"><input id="s-h" type="range" min={1} max={40} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="flex-1 accent-black" /><span className="w-14 text-right font-mono">{hours} h</span></div>
          </div>
          <div className="flex justify-between gap-3">
            <Button variant="secondary" onClick={() => router.push("/onboarding")}>Update interests & skills</Button>
            <Button onClick={save}>Save changes</Button>
          </div>
        </Card>
      </section>

      <section className="mt-14">
        <SectionTitle>Privacy & data</SectionTitle>
        <Card className="divide-y divide-line">
          <div className="flex flex-col justify-between gap-3 p-6 sm:flex-row sm:items-center">
            <div><p className="font-medium">Export your data</p><p className="text-[14px] text-fg-2">Download your profile, roadmaps, evidence and conversations as JSON.</p></div>
            <Button variant="secondary" onClick={exportData}><Download /> Export</Button>
          </div>
          {isDemo ? (
            <div className="flex flex-col justify-between gap-3 p-6 sm:flex-row sm:items-center">
              <div><p className="font-medium">Reset demo profile</p><p className="text-[14px] text-fg-2">Restore the demo account to its original state.</p></div>
              <Button variant="secondary" onClick={resetDemo}><RotateCcw /> Reset</Button>
            </div>
          ) : (
            <div className="flex flex-col justify-between gap-3 p-6 sm:flex-row sm:items-center">
              <div><p className="font-medium">Delete account</p><p className="text-[14px] text-fg-2">Permanently delete your account, uploaded files and all associated data.</p></div>
              <Button variant="danger" onClick={() => setConfirmOpen(true)}><Trash2 /> Delete</Button>
            </div>
          )}
        </Card>
        <p className="mt-3 text-[13px] text-muted">Your profile is private to you. Uploaded certificates and mentor conversations are encrypted at rest.</p>
      </section>

      {status.data && (
        <section className="mt-14">
          <SectionTitle>System</SectionTitle>
          <Card className="grid gap-4 p-6 text-[14px] sm:grid-cols-2">
            <p><span className="text-muted">AI provider:</span> {status.data.ai.available ? `${status.data.ai.provider} · ${status.data.ai.model}` : "Offline mode (no API key)"}</p>
            <p><span className="text-muted">Retrieval:</span> {status.data.rag?.embedder} · {status.data.rag?.fusion}</p>
            <p><span className="text-muted">Knowledge graph:</span> {status.data.graph}</p>
            <p><span className="text-muted">Database:</span> {status.data.database} · cache {status.data.cache}</p>
          </Card>
        </section>
      )}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogTitle className="text-[20px] font-semibold">Delete your account?</DialogTitle>
          <DialogDescription className="mt-2 text-[14px] text-fg-2">This permanently removes your profile, roadmaps, evidence, uploaded files and conversations. Type <b>delete</b> to confirm.</DialogDescription>
          <Input className="mt-5" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
          <Button variant="danger" className="mt-4 w-full" disabled={confirmText !== "delete"} onClick={deleteAccount}>Delete permanently</Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
