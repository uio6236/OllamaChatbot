import React from 'react';
import Dashboard from '@/pages/dashboard/Dashboard.jsx';
import { ChatPanel } from '@/pages/chatbot/ChatPanel.jsx';
import { dashboardReply } from '@/utils/dashboard-model.js';
import { Donut } from '@/components/common/site-primitives.jsx';

// 대시보드와 상담 카드에 기존 입력값을 전달합니다.
export default function DashboardPage({ data, transactions, go, startSim, normalInput }) {
  return (
    <Dashboard
      data={data}
      transactions={transactions}
      startSim={startSim}
      normalInput={normalInput}
      go={go}
      chart={(rows) => <Donut transactions={rows} />}
      chat={<ChatPanel data={data} reply={dashboardReply} />}
    />
  );
}
