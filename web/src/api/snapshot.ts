// src/api/snapshot.ts
const API_BASE = '/snapshot'  // ✅ 直接以 /snapshot 开头

export function getAutoStatus() {
  return fetch(`${API_BASE}/auto-status`)
    .then(res => {
      if (!res.ok) throw new Error('获取状态失败')
      return res.json()
    })
}

export function toggleAutoSnapshot() {
  return fetch(`${API_BASE}/auto-toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  }).then(res => {
    if (!res.ok) throw new Error('切换自动快照失败')
    return res.json()
  })
}

export function triggerSnapshot() {
  return fetch(`${API_BASE}/blockstock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  }).then(res => {
    if (!res.ok) throw new Error('手动触发快照失败')
    return res.json()
  })
}