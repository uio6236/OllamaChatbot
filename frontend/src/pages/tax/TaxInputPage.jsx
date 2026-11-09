import React from 'react';
import TaxInfoForm from '@/pages/tax/TaxInfoForm.jsx';

// 일반 입력·시뮬레이션 모드에 맞는 기존 폼 상태를 연결합니다.
export default function TaxInputPage({
  data,
  onTaxYearChange,
  transactions,
  mode,
  session,
  upload,
  simTx,
  simUpload,
  formSeed,
  go,
  calculate,
  sim,
}) {
  return (
    <TaxInfoForm
      onTaxYearChange={onTaxYearChange}
      key={formSeed + '-' + session?.id + '-' + JSON.stringify(mode === 'simulation' ? sim : data)}
      mode={mode}
      data={mode === 'simulation' ? sim : data}
      transactions={mode === 'simulation' ? simTx : transactions}
      upload={mode === 'simulation' ? simUpload : upload}
      onSubmit={calculate}
      onCancel={() => go('dashboard')}
    />
  );
}
