'use client';

import Link from 'next/link';

export default function AboutPage() {
    const features = [
        {
            title: "Smart Document Analysis",
            description: "Upload your contracts, agreements, or legal documents and let our AI instantly analyze them for risks, opportunities, and key insights.",
            icon: "📄",
            benefits: ["Instant risk detection", "Key clause identification", "Compliance checking"]
        },
        {
            title: "Risk Assessment",
            description: "Get comprehensive risk scores and detailed explanations of potential issues in plain English, not legal jargon.",
            icon: "⚠️",
            benefits: ["Clear risk ratings", "Plain English explanations", "Actionable recommendations"]
        },
        {
            title: "Intelligent Search",
            description: "Find specific information across all your documents using natural language. Ask questions like 'What are my payment terms?'",
            icon: "🔍",
            benefits: ["Natural language queries", "Instant results", "Cross-document search"]
        },
        {
            title: "Real-time Analytics",
            description: "Track your document portfolio with beautiful dashboards showing trends, risks, and opportunities at a glance.",
            icon: "📊",
            benefits: ["Visual dashboards", "Trend analysis", "Performance metrics"]
        }
    ];

    const useCases = [
        {
            industry: "Legal Firms",
            challenge: "Reviewing hundreds of contracts manually",
            solution: "Automated contract analysis and risk detection",
            result: "90% faster document review process"
        },
        {
            industry: "Real Estate",
            challenge: "Managing complex property agreements",
            solution: "Intelligent document organization and search",
            result: "Instant access to critical contract terms"
        },
        {
            industry: "Healthcare",
            challenge: "Ensuring compliance across vendor contracts",
            solution: "Automated compliance checking and alerts",
            result: "100% compliance monitoring coverage"
        },
        {
            industry: "Finance",
            challenge: "Risk assessment of loan documents",
            solution: "AI-powered risk scoring and analysis",
            result: "Enhanced decision-making accuracy"
        }
    ];

    return (
        <div className="min-h-screen bg-white">
            {/* Hero Section */}
            <section className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-purple-50">
                <div className="absolute inset-0">
                    <img
                        src="/backgrounds/home-hero-bg.svg"
                        alt=""
                        className="w-full h-full object-cover opacity-30"
                    />
                </div>

                <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
                    <div className="text-center">
                        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
                            Transform Your Document
                            <span className="block bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                                Intelligence
                            </span>
                        </h1>
                        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
                            DocuShield uses advanced AI to help businesses understand, analyze, and manage their documents like never before.
                            No technical expertise required – just upload your documents and get instant insights.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Link
                                href="/upload"
                                className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-all duration-200 hover:shadow-lg hover:-translate-y-1"
                            >
                                Try DocuShield
                            </Link>
                            <Link
                                href="#how-it-works"
                                className="bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold border-2 border-blue-600 hover:bg-blue-50 transition-all duration-200 hover:shadow-lg hover:-translate-y-1"
                            >
                                See How It Works
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* What We Do Section */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">What DocuShield Does</h2>
                        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                            We make complex document analysis simple. Our AI reads your documents like an expert lawyer,
                            accountant, and analyst combined – but faster and more accurate.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
                        {features.map((feature, index) => (
                            <div
                                key={index}
                                className="bg-white rounded-xl p-8 shadow-lg border border-gray-100 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 cursor-pointer"

                            >
                                <div className="text-4xl mb-4">{feature.icon}</div>
                                <h3 className="text-xl font-semibold text-gray-900 mb-3">{feature.title}</h3>
                                <p className="text-gray-600 mb-4">{feature.description}</p>
                                <ul className="space-y-2">
                                    {feature.benefits.map((benefit, idx) => (
                                        <li key={idx} className="flex items-center text-sm text-gray-500">
                                            <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                            {benefit}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* How It Works Section */}
            <section id="how-it-works" className="py-20 bg-gray-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">How DocuShield Works</h2>
                        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                            Three simple steps to transform your document management
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-12">
                        <div className="text-center">
                            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="text-2xl font-bold text-blue-600">1</span>
                            </div>
                            <h3 className="text-2xl font-semibold text-gray-900 mb-4">Upload Documents</h3>
                            <p className="text-gray-600 mb-6">
                                Simply drag and drop your contracts, agreements, or any business documents.
                                We support PDF, Word, and text files.
                            </p>
                            <div className="bg-white rounded-lg p-6 shadow-md">
                                <img src="/illustrations/upload-step.svg" alt="Upload documents" className="w-full h-32 object-contain" />
                            </div>
                        </div>

                        <div className="text-center">
                            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="text-2xl font-bold text-green-600">2</span>
                            </div>
                            <h3 className="text-2xl font-semibold text-gray-900 mb-4">AI Analysis</h3>
                            <p className="text-gray-600 mb-6">
                                Our advanced AI reads and understands your documents, identifying risks,
                                key terms, and important clauses in seconds.
                            </p>
                            <div className="bg-white rounded-lg p-6 shadow-md">
                                <img src="/illustrations/analysis-step.svg" alt="AI analysis" className="w-full h-32 object-contain" />
                            </div>
                        </div>

                        <div className="text-center">
                            <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="text-2xl font-bold text-purple-600">3</span>
                            </div>
                            <h3 className="text-2xl font-semibold text-gray-900 mb-4">Get Insights</h3>
                            <p className="text-gray-600 mb-6">
                                Receive clear, actionable insights with risk scores, summaries,
                                and recommendations in plain English.
                            </p>
                            <div className="bg-white rounded-lg p-6 shadow-md">
                                <img src="/illustrations/insights-step.svg" alt="Get insights" className="w-full h-32 object-contain" />
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Use Cases Section */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">Who Uses DocuShield</h2>
                        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                            From small businesses to large enterprises, DocuShield helps organizations across industries
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 gap-8">
                        {useCases.map((useCase, index) => (
                            <div key={index} className="bg-gradient-to-br from-gray-50 to-white rounded-xl p-8 shadow-lg border border-gray-100">
                                <h3 className="text-2xl font-semibold text-gray-900 mb-4">{useCase.industry}</h3>
                                <div className="space-y-4">
                                    <div>
                                        <h4 className="font-semibold text-red-600 mb-2">Challenge:</h4>
                                        <p className="text-gray-600">{useCase.challenge}</p>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-blue-600 mb-2">DocuShield Solution:</h4>
                                        <p className="text-gray-600">{useCase.solution}</p>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-green-600 mb-2">Result:</h4>
                                        <p className="text-gray-600 font-medium">{useCase.result}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Technology & Architecture Section */}
            <section className="py-20 bg-gray-900 text-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold mb-4">Demo Technology Stack</h2>
                        <p className="text-xl text-gray-300 max-w-3xl mx-auto">
                            This is a demonstration project showcasing modern document processing technologies.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="text-center">
                            <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold mb-3">Multi-LLM Architecture</h3>
                            <p className="text-gray-300">Integrates OpenAI, Anthropic, Gemini, and Groq APIs for diverse AI capabilities.</p>
                        </div>

                        <div className="text-center">
                            <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold mb-3">Modern Tech Stack</h3>
                            <p className="text-gray-300">Built with Next.js, FastAPI, TiDB, AWS services, and modern development practices.</p>
                        </div>

                        <div className="text-center">
                            <div className="w-16 h-16 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold mb-3">Open Source Demo</h3>
                            <p className="text-gray-300">This is a demonstration project for learning and showcasing AI document processing.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
                <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
                    <h2 className="text-4xl font-bold text-white mb-6">
                        Ready to Explore DocuShield Demo?
                    </h2>
                    <p className="text-xl text-blue-100 mb-8">
                        Experience AI-powered document analysis in this interactive demonstration platform.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Link
                            href="/upload"
                            className="bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-100 transition-all duration-200 hover:shadow-lg hover:-translate-y-1"
                        >
                            Try DocuShield
                        </Link>
                        <Link
                            href="/demo"
                            className="bg-transparent text-white px-8 py-4 rounded-lg text-lg font-semibold border-2 border-white hover:bg-white hover:text-blue-600 transition-all duration-200"
                        >
                            View Features
                        </Link>
                    </div>
                    <p className="text-blue-100 text-sm mt-6">
                        Demo project • Educational purposes • No registration required
                    </p>
                </div>
            </section>
        </div>
    );
}