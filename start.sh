#!/usr/bin/env bash
# Desktop convenience entry; simulation and flight still use tools/project.sh.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT"
ACTION=${1:-start}
case "$ACTION" in
  start|fly|status|stop) ;;
  -h|--help|help)
    echo '用法: ./start.sh [start|fly|status|stop]'
    echo 'start: 打开 Gazebo + RViz（默认，不起飞）'
    echo 'fly:   前检 → 起飞 → 默认16米导航 → 降落上锁'
    echo 'status: 查看当前会话与最近任务结果；stop: 结束已落地的会话'
    exit 0 ;;
  *) echo '未知命令；使用 ./start.sh --help' >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { echo '只接受一个命令；使用 ./start.sh --help' >&2; exit 2; }
if [[ "$ACTION" != status ]]; then
  mkdir -p .runtime
  exec 9>.runtime/start.lock
  flock -n 9 || { echo '已有启动或飞行命令在执行；使用 ./start.sh status 查看进度。' >&2; exit 9; }
fi
docker info >/dev/null 2>&1 || { echo '无法访问 Docker，请检查服务与当前用户的 docker 组权限。' >&2; exit 1; }
ACTIVE=$(docker ps --filter "label=d435i.project=$ROOT" --format '{{.Names}}')
[[ "$ACTIVE" != *$'\n'* ]] || { echo '发现多个本项目会话，请先检查 Docker。' >&2; exit 9; }
RUN_ID=${ACTIVE#d435i-}

detect_desktop() {
  command -v xdpyinfo >/dev/null || { echo '缺少 xdpyinfo，请安装 x11-utils。' >&2; return 1; }
  if [[ -n "${DISPLAY:-}" && -r "${XAUTHORITY:-$HOME/.Xauthority}" ]] &&
      timeout 3 env XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" xdpyinfo >/dev/null 2>&1; then
    export XAUTHORITY=${XAUTHORITY:-$HOME/.Xauthority}
    return
  fi
  local candidate authority
  # Xorg exposes the actual desktop display and authority, including XRDP sessions.
  while read -r candidate authority; do
    [[ -z "${DISPLAY:-}" || "$DISPLAY" == "$candidate" ]] || continue
    [[ -r "$authority" ]] || continue
    if timeout 3 env DISPLAY="$candidate" XAUTHORITY="$authority" xdpyinfo >/dev/null 2>&1; then
      export DISPLAY=$candidate XAUTHORITY=$authority
      return
    fi
  done < <(ps -u "$(id -u)" -o args= | awk '
    /\/Xorg / {
      display=""; auth=""
      for (i=1;i<=NF;i++) {
        if ($i ~ /^:[0-9]+$/) display=$i
        if ($i == "-auth") auth=$(i+1)
      }
      if (display != "" && auth != "") print display, auth
    }')
  echo '没有找到可连接的桌面。请先登录远程桌面，或设置 DISPLAY 和 XAUTHORITY。' >&2
  return 1
}

require_finished_flight() {
  python3 - "$ROOT/artifacts/runs/$RUN_ID" <<'PY'
import json
from pathlib import Path
import sys
run = Path(sys.argv[1])
if any((run / name).exists() for name in ['flight-probe-ready', 'preflight.json', 'flight.json']):
    report = run / 'flight.json'
    result = json.loads(report.read_text()) if report.exists() else {}
    if not result.get('landed_and_disarmed'):
        sys.exit('任务尚未确认落地上锁，拒绝关闭或重启；请等待任务结束。')
    if result.get('result') == 'PASS' and not (run / 'qualification.json').exists():
        sys.exit('任务评估尚未完成，请稍后再试。')
PY
}

start_gui() {
  if [[ -n "$ACTIVE" ]]; then
    [[ "$(docker inspect --format '{{json .Config.Env}}' "$ACTIVE")" == *'"PROJECT_GUI=1"'* ]] || {
      echo '当前是无界面会话；请先结束任务并用 ./start.sh stop 关闭，再启动界面。' >&2; return 1;
    }
    echo "已有会话: $RUN_ID"
    return
  fi
  detect_desktop
  RUN_ID="gui-$(date +%Y%m%d-%H%M%S)-$$"
  echo "启动会话 $RUN_ID，桌面 $DISPLAY"
  bash tools/project.sh sim "$RUN_ID" --gui
  for ((i=0;i<120;i++)); do
    if [[ "$(docker inspect --format '{{.State.Running}}' "d435i-$RUN_ID")" != true ]]; then
      docker logs --tail 25 "d435i-$RUN_ID" >&2
      echo '仿真启动失败，请检查上述日志。' >&2
      return 1
    fi
    if [[ -f "artifacts/runs/$RUN_ID/stack-started" ]]; then
      echo "仿真已启动。日志: $ROOT/artifacts/runs/$RUN_ID"
      return
    fi
    sleep 1
  done
  echo "启动等待超时；保留会话 $RUN_ID 供检查，不执行起飞。" >&2
  return 1
}

case "$ACTION" in
  start) start_gui ;;
  fly)
    if [[ -n "$ACTIVE" ]] && [[ -e "artifacts/runs/$RUN_ID/flight-probe-ready" ||
        -e "artifacts/runs/$RUN_ID/preflight.json" || -e "artifacts/runs/$RUN_ID/flight.json" ]]; then
      require_finished_flight
      bash tools/project.sh stop "$RUN_ID"
      ACTIVE=''
    fi
    start_gui
    echo '开始前检与飞行演示，请保持终端运行，等待自动降落和结果。'
    bash tools/project.sh mission "$RUN_ID"
    ;;
  status)
    [[ -n "$ACTIVE" ]] || { echo '当前没有运行中的本项目会话。'; exit 0; }
    echo "当前会话: $RUN_ID"
    echo "日志目录: $ROOT/artifacts/runs/$RUN_ID"
    python3 - "artifacts/runs/$RUN_ID" <<'PY'
import json
from pathlib import Path
import sys
run = Path(sys.argv[1])
if (run / 'qualification.json').exists():
    result = json.loads((run / 'qualification.json').read_text())
    print('最近任务: ' + ('全部检查通过，已落地上锁' if result['passed'] else '评估未通过，请查看报告'))
elif (run / 'flight.json').exists():
    result = json.loads((run / 'flight.json').read_text())
    print(f"最近飞行: {result['result']}；已落地上锁: {result['landed_and_disarmed']}")
elif (run / 'flight-probe-ready').exists():
    print('任务前检或飞行中，请等待自动降落；进度见 flight.log / live-progress.json。')
else:
    print('界面会话，尚未执行起飞任务。')
PY
    ;;
  stop)
    [[ -n "$ACTIVE" ]] || { echo '当前没有运行中的本项目会话。'; exit 0; }
    require_finished_flight
    exec bash tools/project.sh stop "$RUN_ID"
    ;;
esac
