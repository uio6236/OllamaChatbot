import React from 'react';
import GroupStats from '@/pages/statistics/GroupStats.jsx';

// 기존 그룹 통계 컴포넌트에 사용자 조건을 전달합니다.
export default function StatisticsPage({ data, go }) {
  return <GroupStats data={data} go={go} />;
}
