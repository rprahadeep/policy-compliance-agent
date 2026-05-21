export const QUESTION_TEMPLATES = [
  {
    title: "Privileged access",
    category: "Identification and Authentication",
    question: "Do privileged user accounts need multi-factor authentication before accessing company systems?",
    context: "Employee is requesting elevated access to an internal production administration console.",
  },
  {
    title: "Unexpected data exposure",
    category: "Information Security",
    question: "If I accidentally view customer data that is unrelated to my project, should I report it?",
    context: "The employee saw records in a shared internal dashboard and did not download or share them.",
  },
  {
    title: "Vendor system purchase",
    category: "System and Services Acquisition",
    question: "What compliance checks are required before buying a new SaaS tool that stores company data?",
    context: "The team wants to onboard a vendor quickly for project tracking and document exchange.",
  },
  {
    title: "Security assessment",
    category: "Security Assessment and Authorization",
    question: "When does a system need security assessment and authorization before it can be used?",
    context: "A business unit wants to launch a new workflow tool for internal users.",
  },
];

export const CONTEXT_PRESETS = [
  "Urgent business request",
  "Customer data involved",
  "Privileged account involved",
  "Third-party vendor involved",
  "Possible security incident",
];
