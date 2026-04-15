import { useEffect, useState } from 'react';
import { benchmarksApi } from '../api/client';
import Spinner from './Spinner';
import LatencyHistogram from './charts/LatencyHistogram';
import ProfileComparison from './charts/ProfileComparison';
import TokenEconomyRunChart from './charts/TokenEconomyRunChart';

export default function AnalysisTab({ benchmarkId }) {
  const [profileStats, setProfileStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    benchmarksApi.profileStats(benchmarkId).then((res) => {
      if (!cancelled) {
        setProfileStats(res.data);
        setLoading(false);
      }
    }).catch(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [benchmarkId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 gap-2 text-gray-500 text-sm">
        <Spinner size="sm" />
        Loading analysis...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <LatencyHistogram benchmarkId={benchmarkId} profiles={profileStats} />
      <TokenEconomyRunChart profileStats={profileStats} />
      <ProfileComparison profileStats={profileStats} />
    </div>
  );
}
