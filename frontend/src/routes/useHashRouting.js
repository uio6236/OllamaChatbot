import { useEffect } from 'react';
import { accountService } from '@/api/account-service.js';
import { recordAccess } from '@/api/prototype-records.js';

// 원본 해시 라우터를 그대로 분리했습니다. #dashboard 등 주소와 뒤로/앞으로 가기를 유지합니다.
// features/how는 랜딩의 앵커이며 expenses는 원본처럼 input으로 연결됩니다.
export function useHashRouting({ setPage, setMode, setFormSeed, setMobile }) {
  useEffect(() => {
    const handle = () => {
      const route = location.hash.slice(1) || 'home';
      if (['features', 'how'].includes(route)) return;
      if (route === 'admin')
        recordAccess(
          'ADMIN_VIEW',
          accountService.current()?.role === 'ADMIN' ? 'SUCCESS' : 'DENIED',
        );
      if (route === 'expenses') {
        setMode('normal');
        setFormSeed((s) => s + 1);
        setPage('input');
        location.hash = 'input';
        return;
      }
      setPage(route);
      setMobile(false);
    };
    handle();
    window.addEventListener('hashchange', handle);
    return () => window.removeEventListener('hashchange', handle);
  }, []);
}
