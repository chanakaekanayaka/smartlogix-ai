import { BuildingIcon, CheckIcon, PackageIcon, TruckIcon, WarehouseIcon } from './icons'

// Kept in sync with docs/COMMERCIALIZATION.md and the tiers already
// presented at Mid Evaluation - this is the B2B SaaS pricing model for
// licensing SmartLogix itself to a logistics business, not the per-shipment
// customer cost shown in PricingPanel.jsx.
const PLANS = [
  {
    name: 'Free',
    icon: PackageIcon,
    price: '$0',
    period: '/ month',
    tagline: 'For very small businesses',
    features: [
      '10 delivery estimates / month',
      'Chat widget (policy Q&A)',
      'Community support',
    ],
    cta: 'Start free',
    highlighted: false,
  },
  {
    name: 'Basic',
    icon: TruckIcon,
    price: '$29',
    period: '/ month',
    tagline: 'For small delivery companies',
    features: [
      'Higher monthly query volume',
      '1 warehouse',
      'Email support',
    ],
    cta: 'Get started',
    highlighted: false,
  },
  {
    name: 'Pro',
    icon: WarehouseIcon,
    price: '$99',
    period: '/ month',
    tagline: 'For medium businesses - unlimited use',
    features: [
      'Unlimited delivery-plan queries',
      'Multiple warehouses',
      'Your own knowledge-base content',
      'Usage analytics dashboard',
      'Priority support',
    ],
    cta: 'Talk to sales',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    icon: BuildingIcon,
    price: 'Custom',
    period: '',
    tagline: 'For large logistics companies',
    features: [
      'Unlimited everything',
      'Private / on-premise deployment',
      'SLA-backed uptime',
      'Dedicated account manager',
      'White-label branding',
    ],
    cta: 'Contact us',
    highlighted: false,
  },
]

/**
 * B2B pricing page for "SmartLogix for Business" - the SaaS product being
 * licensed to logistics companies, as distinct from the per-shipment cost
 * a customer sees for their own delivery (see PricingPanel.jsx).
 */
export default function PricingPlans() {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
          SmartLogix for Business
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
          License the multi-agent SmartLogix pipeline for your own logistics
          operation - instant, explainable delivery plans for your customers,
          with a built-in Responsible AI trail.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((plan) => (
          <PlanCard key={plan.name} plan={plan} />
        ))}
      </div>

      <div className="mx-auto flex max-w-md items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 shadow-sm">
        <span className="rounded-full bg-brand-50 px-2 py-0.5 font-semibold text-brand-700">
          API licensing
        </span>
        $0.10-0.20 / request - for other apps embedding SmartLogix directly
      </div>

      <p className="text-center text-[11px] leading-tight text-slate-400">
        Illustrative pricing for this academic project - see{' '}
        <span className="font-medium text-slate-500">docs/COMMERCIALIZATION.md</span>{' '}
        for the full commercialization strategy.
      </p>
    </div>
  )
}

function PlanCard({ plan }) {
  const Icon = plan.icon
  return (
    <div
      className={`card relative flex flex-col ${
        plan.highlighted ? 'ring-2 ring-brand-500 shadow-elevated' : ''
      }`}
    >
      {plan.highlighted && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-600 px-3 py-1 text-[11px] font-semibold text-white shadow-glow">
          Most popular
        </span>
      )}

      <div className="card-body flex flex-1 flex-col">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-50 to-brand-100 text-brand-600 ring-1 ring-brand-600/10">
          <Icon className="h-4.5 w-4.5" />
        </span>

        <h3 className="mt-3 text-base font-bold text-slate-900">{plan.name}</h3>
        <p className="mt-1 text-xs text-slate-500">{plan.tagline}</p>

        <div className="mt-4 flex items-baseline gap-1">
          <span className="text-2xl font-extrabold tracking-tight text-slate-900">
            {plan.price}
          </span>
          <span className="text-xs font-medium text-slate-400">{plan.period}</span>
        </div>

        <ul className="mt-4 flex-1 space-y-2">
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2 text-sm text-slate-600">
              <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
              {feature}
            </li>
          ))}
        </ul>

        <button
          type="button"
          className={`mt-5 inline-flex items-center justify-center rounded-full px-4 py-2.5 text-sm font-semibold shadow-sm transition-all duration-200 hover:-translate-y-0.5 ${
            plan.highlighted
              ? 'bg-brand-600 text-white shadow-glow hover:bg-brand-700'
              : 'border border-slate-200 bg-white text-slate-700 hover:border-brand-300 hover:text-brand-700'
          }`}
        >
          {plan.cta}
        </button>
      </div>
    </div>
  )
}
