export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          exlm - Domain-Specific LLM Automation Platform
        </h1>
        <p className="text-center text-gray-600 mb-12">
          오픈소스 LLM 파인튜닝부터 합성 데이터 생성, 최신 학습 기법 적용, 
          그리고 프로덕션 서빙까지 전체 파이프라인을 자동화합니다.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 border rounded-lg hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-semibold mb-3">🤖 모델 관리</h2>
            <p className="text-gray-600">
              최신 오픈소스 LLM 지원 및 자동 파인튜닝
            </p>
          </div>
          <div className="p-6 border rounded-lg hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-semibold mb-3">📊 데이터 생성</h2>
            <p className="text-gray-600">
              고품질 합성 데이터 생성 및 품질 관리
            </p>
          </div>
          <div className="p-6 border rounded-lg hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-semibold mb-3">🚀 모델 서빙</h2>
            <p className="text-gray-600">
              vLLM 통합 및 OpenAI API 호환 서빙
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}