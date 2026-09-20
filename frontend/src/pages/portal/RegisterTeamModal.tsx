/** 官网：报名建队弹窗。支持团队赛（队名+队友）与个人赛（昵称）。 */

import { useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { TournamentDetail } from "../../types";
import { tournamentApi, ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { Button, ErrorBanner, Field, Input, Modal } from "../../components/ui";

export default function RegisterTeamModal({
  detail,
  open,
  onClose,
  onSuccess,
}: {
  detail: TournamentDetail;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { user } = useAuth();
  const isSolo = detail.team_mode === 2;
  const maxTeammates = Math.max(0, detail.max_team_members - 1);

  const [teamName, setTeamName] = useState("");
  const [nickname, setNickname] = useState("");
  const [teammates, setTeammates] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const reset = () => {
    setTeamName("");
    setNickname("");
    setTeammates([]);
    setError("");
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const body: Record<string, unknown> = {};
    if (isSolo) {
      if (!nickname.trim()) {
        setError("请填写你的参赛昵称");
        return;
      }
      body.name = nickname.trim();
      body.players = [];
    } else {
      if (!teamName.trim()) {
        setError("请填写队伍名");
        return;
      }
      body.name = teamName.trim();
      body.players = teammates
        .filter((t) => t.trim())
        .map((t) => ({ nickname: t.trim() }));
    }

    setLoading(true);
    try {
      await tournamentApi.createTeam(detail.id, body);
      reset();
      onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "报名失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title={isSolo ? "报名参赛" : "创建队伍报名"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={submit} loading={loading} form="register-form" type="submit">
            提交报名
          </Button>
        </>
      }
    >
      <form id="register-form" onSubmit={submit} className="space-y-4">
        {isSolo ? (
          <Field label="参赛昵称" required hint="个人赛以你的昵称作为队伍名参赛">
            <Input
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="例如：阿强"
              maxLength={64}
            />
          </Field>
        ) : (
          <>
            <Field
              label="队伍名"
              required
              hint={`队长为 ${user?.nickname ?? "你"}，自动加入队伍`}
            >
              <Input
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                placeholder="例如：小虎队"
                maxLength={64}
              />
            </Field>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                队友昵称（选填，最多 {maxTeammates} 人）
              </label>
              <div className="space-y-2">
                {teammates.map((t, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      value={t}
                      onChange={(e) =>
                        setTeammates((prev) =>
                          prev.map((v, j) => (j === i ? e.target.value : v)),
                        )
                      }
                      placeholder={`队友 ${i + 1} 昵称`}
                      maxLength={64}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setTeammates((prev) => prev.filter((_, j) => j !== i))}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>
              {teammates.length < maxTeammates && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="mt-2"
                  onClick={() => setTeammates((prev) => [...prev, ""])}
                >
                  <Plus className="h-3.5 w-3.5" /> 添加队友
                </Button>
              )}
            </div>
          </>
        )}
        {error && <ErrorBanner message={error} />}
        <p className="text-xs text-gray-400">
          报名后需办赛者审核确认；请确保队员昵称准确，确认后可在报名管理中补充。
        </p>
      </form>
    </Modal>
  );
}
