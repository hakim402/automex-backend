"""
Management command to seed the database with sample data for:
  - Portfolio Projects
  - Blog Authors
  - AI Capabilities
  - Tech Expertise Areas
  - Partners
  - Certifications
  - Service Detail Pages (hero images, deliverables, add-ons,
    comparison rows, client logos, testimonials, documents, SLAs)
  - Support Tickets

Usage:
    docker compose exec web python manage.py seed_data
    docker compose exec web python manage.py seed_data --clear   # delete existing first
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.accounts.models import User
from apps.content.models import (
    AICapability,
    BlogAuthor,
    Certification,
    Industry,
    Partner,
    PortfolioProject,
    Service,
    ServiceAddOn,
    ServiceClientLogo,
    ServiceComparisonRow,
    ServiceDeliverable,
    ServiceDocument,
    ServiceHeroImage,
    ServiceSLA,
    ServiceTestimonial,
    TechExpertiseArea,
    Technology,
    Testimonial,
)
from apps.crm.models import SupportTicket


class Command(BaseCommand):
    help = "Seed the database with sample enterprise data for all models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing seeded data before re-creating.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()

        svc = list(Service.objects.all())
        techs = list(Technology.objects.all())
        industries = list(Industry.objects.all())
        testimonials = list(Testimonial.objects.all())
        admin_user = User.objects.filter(is_staff=True).first()

        # ── fallback: create a system user if no staff user exists ─────
        if not admin_user:
            admin_user = User.objects.filter(deleted_at__isnull=True).first()

        self._seed_portfolio(svc, techs, industries)
        self._seed_blog_authors()
        self._seed_ai_capabilities(svc, techs)
        self._seed_tech_expertise(techs)
        self._seed_partners()
        self._seed_certifications(svc)

        if svc:
            svc0 = svc[0]
            self._seed_service_hero_images(svc0)
            self._seed_service_deliverables(svc0)
            self._seed_service_addons(svc0)
            self._seed_service_comparison_rows(svc0)
            self._seed_service_client_logos(svc0)
            self._seed_service_testimonials(svc0, testimonials)
            self._seed_service_documents(svc0)
            self._seed_service_slas(svc0)

        self._seed_support_tickets(admin_user, svc)

        self.stdout.write(self.style.SUCCESS("\n✅ All seed data created successfully."))

    # ──────────────────────────────────────────────────────────────────────
    # CLEAR
    # ──────────────────────────────────────────────────────────────────────

    def _clear(self):
        models = [
            (SupportTicket, "support tickets"),
            (ServiceSLA, "service SLAs"),
            (ServiceDocument, "service documents"),
            (ServiceTestimonial, "service testimonials"),
            (ServiceClientLogo, "service client logos"),
            (ServiceComparisonRow, "service comparison rows"),
            (ServiceAddOn, "service add-ons"),
            (ServiceDeliverable, "service deliverables"),
            (ServiceHeroImage, "service hero images"),
            (Certification, "certifications"),
            (Partner, "partners"),
            (TechExpertiseArea, "tech expertise areas"),
            (AICapability, "AI capabilities"),
            (BlogAuthor, "blog authors"),
            (PortfolioProject, "portfolio projects"),
        ]
        for model, label in models:
            count, _ = model.objects.all().delete()
            self.stdout.write(f"  🗑  Cleared {count} {label}")

    # ──────────────────────────────────────────────────────────────────────
    # PORTFOLIO PROJECTS
    # ──────────────────────────────────────────────────────────────────────

    def _seed_portfolio(self, services, technologies, industries):
        projects = [
            {
                "title": "Global E-Commerce Platform Migration",
                "short_description": "Migrated a legacy monolith serving 2M+ monthly users to a cloud-native microservices architecture with zero downtime.",
                "client_name": "ShopStream Inc.",
                "completion_year": 2025,
                "is_featured": True,
                "project_url": "https://shopstream.com",
            },
            {
                "title": "AI-Powered Fraud Detection System",
                "short_description": "Built a real-time fraud detection engine processing 500K transactions/day using ensemble ML models.",
                "client_name": "FinGuard Banking",
                "completion_year": 2024,
                "is_featured": True,
                "project_url": "",
            },
            {
                "title": "Healthcare Patient Portal Redesign",
                "short_description": "Designed and delivered a HIPAA-compliant patient portal serving 50+ clinics with integrated telehealth.",
                "client_name": "MediConnect Health",
                "completion_year": 2025,
                "is_featured": False,
                "project_url": "https://mediconnect.example.com",
            },
            {
                "title": "Smart Logistics Dashboard",
                "short_description": "Real-time fleet tracking and route optimization dashboard reducing delivery times by 23%.",
                "client_name": "RapidRoute Logistics",
                "completion_year": 2024,
                "is_featured": False,
                "project_url": "",
            },
            {
                "title": "EdTech Learning Management System",
                "short_description": "Scalable LMS with adaptive learning paths, serving 200K+ students across 12 countries.",
                "client_name": "EduNova",
                "completion_year": 2025,
                "is_featured": True,
                "project_url": "https://edunova.io",
            },
        ]
        for i, p in enumerate(projects):
            obj, created = PortfolioProject.objects.update_or_create(
                slug=slugify(p["title"]),
                defaults={
                    **p,
                    "industry": random.choice(industries) if industries else None,
                    "is_published": True,
                    "order": i + 1,
                },
            )
            if created and services:
                obj.services.add(random.choice(services))
            if created and technologies:
                obj.technologies.add(*random.sample(technologies, min(3, len(technologies))))
            self.stdout.write(f"  {'✅' if created else '⏭ '} Portfolio: {obj.title}")

    # ──────────────────────────────────────────────────────────────────────
    # BLOG AUTHORS
    # ──────────────────────────────────────────────────────────────────────

    def _seed_blog_authors(self):
        authors = [
            {"full_name": "Dr. Sarah Chen", "role_title": "Chief AI Architect", "bio": "15+ years in ML and NLP. Previously led AI research at DeepMind and authored 30+ papers on transformer architectures.", "linkedin_url": "https://linkedin.com/in/sarahchen", "github_url": "https://github.com/sarahchen"},
            {"full_name": "Marcus Okafor", "role_title": "Lead Cloud Engineer", "bio": "AWS and GCP certified architect specializing in Kubernetes at scale. Built infrastructure serving 10M+ daily requests.", "linkedin_url": "https://linkedin.com/in/marcusokafor", "github_url": "https://github.com/mokafor"},
            {"full_name": "Elena Rodriguez", "role_title": "Head of UX Research", "bio": "Design strategist bridging behavioral psychology and digital products. Former UX lead at IDEO and Fjord.", "linkedin_url": "https://linkedin.com/in/elenarodriguez", "github_url": ""},
            {"full_name": "James Park", "role_title": "Senior Backend Engineer", "bio": "Python/Django specialist focused on API design and distributed systems. Open-source contributor to Django REST Framework.", "linkedin_url": "https://linkedin.com/in/jamespark", "github_url": "https://github.com/jpark-dev"},
            {"full_name": "Aisha Al-Rashid", "role_title": "VP of Engineering", "bio": "Engineering leader with experience scaling teams from 5 to 80+. Formerly at Stripe and Shopify.", "linkedin_url": "https://linkedin.com/in/aishaalrashid", "github_url": ""},
        ]
        for a in authors:
            obj, created = BlogAuthor.objects.update_or_create(
                slug=slugify(a["full_name"]),
                defaults={**a, "email": f"{slugify(a['full_name'])}@automex.tech", "is_active": True},
            )
            self.stdout.write(f"  {'✅' if created else '⏭ '} Author: {obj.full_name}")

    # ──────────────────────────────────────────────────────────────────────
    # AI CAPABILITIES
    # ──────────────────────────────────────────────────────────────────────

    def _seed_ai_capabilities(self, services, technologies):
        capabilities = [
            {"name": "Intelligent Document Processing", "category": "nlp", "maturity_level": "production", "description": "Extract, classify, and validate data from unstructured documents using transformer-based OCR and NLP pipelines. Supports 40+ languages.", "icon": "lucide:file-text"},
            {"name": "Predictive Maintenance Engine", "category": "predictive_analytics", "maturity_level": "production", "description": "Real-time equipment failure prediction using IoT sensor data and gradient-boosted decision trees. Reduces unplanned downtime by up to 45%.", "icon": "lucide:wrench"},
            {"name": "Generative Design Copilot", "category": "generative_ai", "maturity_level": "experimental", "description": "AI-assisted UI/UX design generation trained on design systems. Produces Figma-ready components from natural language prompts.", "icon": "lucide:palette"},
            {"name": "Customer Intent Classifier", "category": "nlp", "maturity_level": "production", "description": "Multi-label intent classification for support tickets and chat conversations. 94% accuracy across 50+ intent categories.", "icon": "lucide:brain-circuit"},
            {"name": "Autonomous QA Agent", "category": "rag_agents", "maturity_level": "research", "description": "Self-improving testing agent that generates test cases from code diffs and API specs using RAG over documentation.", "icon": "lucide:test-tubes"},
            {"name": "Real-Time Anomaly Detection", "category": "predictive_analytics", "maturity_level": "production", "description": "Streaming anomaly detection for financial transactions and system metrics using online learning algorithms.", "icon": "lucide:activity"},
            {"name": "Conversational AI Platform", "category": "nlp", "maturity_level": "production", "description": "Multi-turn, context-aware chatbot framework with RAG knowledge retrieval and multi-language support.", "icon": "lucide:message-circle"},
            {"name": "MLOps Pipeline Orchestrator", "category": "mlops", "maturity_level": "production", "description": "End-to-end ML lifecycle management: experiment tracking, model registry, A/B deployment, and drift monitoring.", "icon": "lucide:workflow"},
        ]
        for i, c in enumerate(capabilities):
            obj, created = AICapability.objects.update_or_create(
                slug=slugify(c["name"]),
                defaults={**c, "is_active": True, "order": i + 1},
            )
            if created and services:
                obj.related_services.add(random.choice(services))
            if created and technologies:
                obj.technologies.add(*random.sample(technologies, min(2, len(technologies))))
            self.stdout.write(f"  {'✅' if created else '⏭ '} AI Capability: {obj.name}")

    # ──────────────────────────────────────────────────────────────────────
    # TECH EXPERTISE AREAS
    # ──────────────────────────────────────────────────────────────────────

    def _seed_tech_expertise(self, technologies):
        areas = [
            {"name": "Cloud-Native Architecture", "category": "architecture", "description": "Designing scalable, resilient systems on AWS, GCP, and Azure using microservices, event-driven patterns, and serverless computing.", "icon": "lucide:cloud"},
            {"name": "Kubernetes & Container Orchestration", "category": "cloud", "description": "Production-grade K8s cluster management with GitOps workflows, service mesh (Istio), and auto-scaling policies.", "icon": "lucide:container"},
            {"name": "Data Engineering & Pipelines", "category": "data_engineering", "description": "Building robust ETL/ELT pipelines with Apache Spark, Airflow, and dbt. Real-time streaming with Kafka and Flink.", "icon": "lucide:database"},
            {"name": "Machine Learning Engineering", "category": "ai", "description": "End-to-end ML systems: feature stores, model training at scale, serving infrastructure, and continuous evaluation.", "icon": "lucide:cpu"},
            {"name": "DevSecOps", "category": "security", "description": "Shift-left security with SAST/DAST in CI/CD, container scanning, secrets management, and zero-trust architectures.", "icon": "lucide:shield"},
            {"name": "iOS & Android Development", "category": "mobile", "description": "Native and cross-platform mobile apps with Swift, Kotlin, and React Native. Focus on performance and accessibility.", "icon": "lucide:smartphone"},
            {"name": "CI/CD & Platform Engineering", "category": "devops", "description": "Internal developer platforms with self-service infrastructure, ephemeral environments, and automated compliance checks.", "icon": "lucide:rocket"},
            {"name": "Automated Testing & QA", "category": "qa", "description": "Comprehensive test strategies: unit, integration, e2e, visual regression, performance, and chaos engineering.", "icon": "lucide:check-circle"},
        ]
        for i, a in enumerate(areas):
            obj, created = TechExpertiseArea.objects.update_or_create(
                slug=slugify(a["name"]),
                defaults={**a, "is_active": True, "order": i + 1},
            )
            if created and technologies:
                obj.technologies.add(*random.sample(technologies, min(2, len(technologies))))
            self.stdout.write(f"  {'✅' if created else '⏭ '} Tech Expertise: {obj.name}")

    # ──────────────────────────────────────────────────────────────────────
    # PARTNERS
    # ──────────────────────────────────────────────────────────────────────

    def _seed_partners(self):
        partners = [
            {"name": "Google Cloud", "partner_type": "cloud", "tier": "platinum", "website_url": "https://cloud.google.com", "description": "Premier Google Cloud partner with specialized expertise in AI/ML, Kubernetes, and data analytics."},
            {"name": "Amazon Web Services", "partner_type": "cloud", "tier": "platinum", "website_url": "https://aws.amazon.com", "description": "Advanced AWS Consulting Partner. 50+ AWS certifications across the team."},
            {"name": "Microsoft Azure", "partner_type": "cloud", "tier": "gold", "website_url": "https://azure.microsoft.com", "description": "Gold Cloud Platform partner with Azure Solutions Architect and DevOps Engineer Expert certifications."},
            {"name": "Datadog", "partner_type": "technology", "tier": "gold", "website_url": "https://datadoghq.com", "description": "Authorized monitoring and observability partner. Deep expertise in APM, infrastructure monitoring, and log management."},
            {"name": "Twilio", "partner_type": "integration", "tier": "gold", "website_url": "https://twilio.com", "description": "Communications integration partner. SMS, voice, video, and email API integration specialists."},
            {"name": "Stripe", "partner_type": "integration", "tier": "silver", "website_url": "https://stripe.com", "description": "Payment infrastructure partner. Custom payment flows, subscription billing, and marketplace solutions."},
            {"name": "GitHub", "partner_type": "technology", "tier": "gold", "website_url": "https://github.com", "description": "GitHub Enterprise partner. CI/CD automation with GitHub Actions and Advanced Security."},
            {"name": "Auth0 by Okta", "partner_type": "integration", "tier": "silver", "website_url": "https://auth0.com", "description": "Identity and access management partner. SSO, MFA, and social login integration specialists."},
        ]
        for i, p in enumerate(partners):
            obj, created = Partner.objects.update_or_create(
                slug=slugify(p["name"]),
                defaults={**p, "is_active": True, "order": i + 1},
            )
            self.stdout.write(f"  {'✅' if created else '⏭ '} Partner: {obj.name} ({obj.get_tier_display()})")

    # ──────────────────────────────────────────────────────────────────────
    # CERTIFICATIONS
    # ──────────────────────────────────────────────────────────────────────

    def _seed_certifications(self, services):
        certs = [
            {"name": "AWS Solutions Architect Professional", "issuer": "Amazon Web Services", "credential_id": "AWS-SAP-C02-894562", "issue_date": date(2024, 3, 15), "expiry_date": date(2027, 3, 15)},
            {"name": "Google Professional Cloud Architect", "issuer": "Google Cloud", "credential_id": "GCP-PCA-782341", "issue_date": date(2024, 6, 10), "expiry_date": date(2026, 6, 10)},
            {"name": "Certified Kubernetes Administrator (CKA)", "issuer": "CNCF", "credential_id": "CKA-2400-0198-0100", "issue_date": date(2024, 9, 22), "expiry_date": date(2027, 9, 22)},
            {"name": "ISO 27001 Information Security", "issuer": "BSI Group", "credential_id": "IS-789234", "issue_date": date(2025, 1, 8), "expiry_date": date(2028, 1, 8)},
            {"name": "Microsoft Azure DevOps Engineer Expert", "issuer": "Microsoft", "credential_id": "AZ-400-562891", "issue_date": date(2024, 11, 5), "expiry_date": date(2026, 11, 5)},
            {"name": "Certified Scrum Master (CSM)", "issuer": "Scrum Alliance", "credential_id": "CSM-001478923", "issue_date": date(2024, 2, 18), "expiry_date": date(2026, 2, 18)},
            {"name": "SOC 2 Type II Compliance", "issuer": "AICPA", "credential_id": "SOC2-2025-0342", "issue_date": date(2025, 4, 1), "expiry_date": date(2026, 4, 1)},
            {"name": "Google Professional ML Engineer", "issuer": "Google Cloud", "credential_id": "GCP-MLE-451203", "issue_date": date(2025, 2, 14), "expiry_date": date(2027, 2, 14)},
        ]
        for i, c in enumerate(certs):
            obj, created = Certification.objects.update_or_create(
                name=c["name"],
                issuer=c["issuer"],
                defaults={**c, "is_active": True, "order": i + 1},
            )
            if created and services:
                obj.related_services.add(random.choice(services))
            self.stdout.write(f"  {'✅' if created else '⏭ '} Certification: {obj.name}")

    # ──────────────────────────────────────────────────────────────────────
    # SERVICE DETAIL PAGES (attached to first service)
    # ──────────────────────────────────────────────────────────────────────

    def _seed_service_hero_images(self, service):
        existing = ServiceHeroImage.objects.filter(service=service).count()
        if existing > 0:
            self.stdout.write(f"  ⏭  Service Hero Images: {existing} existing (skipped)")
            return
        for i in range(3):
            ServiceHeroImage.objects.create(
                service=service,
                caption=f"Hero image {i + 1} for {service.safe_translation_getter('name', any_language=True) or service}",
                is_cover=(i == 0),
                order=i + 1,
            )
        self.stdout.write(f"  ✅ Service Hero Images: 3 created")

    def _seed_service_deliverables(self, service):
        deliverables = [
            {"title": "Source Code Repository", "description": "Full source code with Git history, hosted on your preferred platform with CI/CD pipelines configured.", "icon": "lucide:git-branch"},
            {"title": "Technical Documentation", "description": "Comprehensive architecture docs, API references, deployment guides, and runbooks.", "icon": "lucide:book-open"},
            {"title": "Test Suite & Coverage Report", "description": "Complete test suite with unit, integration, and e2e tests. Minimum 85% code coverage.", "icon": "lucide:test-tubes"},
            {"title": "CI/CD Pipeline Configuration", "description": "GitHub Actions / GitLab CI pipeline for automated testing, building, and deployment.", "icon": "lucide:workflow"},
            {"title": "Database Schema & Migration Scripts", "description": "Versioned database migrations with rollback support and seed data scripts.", "icon": "lucide:database"},
            {"title": "Deployment Runbook", "description": "Step-by-step deployment guide covering staging, production, rollback, and disaster recovery.", "icon": "lucide:clipboard-list"},
        ]
        for i, d in enumerate(deliverables):
            obj, created = ServiceDeliverable.objects.get_or_create(
                service=service, title=d["title"],
                defaults={**d, "order": i + 1},
            )
        self.stdout.write(f"  ✅ Service Deliverables: {len(deliverables)} created/updated")

    def _seed_service_addons(self, service):
        addons = [
            {"name": "24/7 Priority Support", "description": "Round-the-clock support with 15-minute response time SLA and dedicated account manager.", "price": 2500.00, "is_included_in_enterprise": True},
            {"name": "Performance Optimization Sprint", "description": "Two-week deep-dive into application performance: profiling, bottleneck resolution, and caching strategy.", "price": 8000.00, "is_included_in_enterprise": False},
            {"name": "Custom Analytics Dashboard", "description": "Tailored business intelligence dashboard with real-time metrics, custom reports, and data export.", "price": 5000.00, "is_included_in_enterprise": True},
            {"name": "Staff Training & Onboarding", "description": "On-site or remote training sessions for your team, including custom curriculum and hands-on workshops.", "price": 3500.00, "is_included_in_enterprise": False},
        ]
        for i, a in enumerate(addons):
            obj, created = ServiceAddOn.objects.get_or_create(
                service=service, name=a["name"],
                defaults={**a, "order": i + 1},
            )
        self.stdout.write(f"  ✅ Service Add-Ons: {len(addons)} created/updated")

    def _seed_service_comparison_rows(self, service):
        rows = [
            {"feature_name": "Dedicated Project Manager", "standard_value": "—", "premium_value": "Shared", "enterprise_value": "Dedicated", "is_highlighted": False},
            {"feature_name": "Response Time SLA", "standard_value": "48 hours", "premium_value": "12 hours", "enterprise_value": "4 hours", "is_highlighted": True},
            {"feature_name": "Code Reviews", "standard_value": "Peer review", "premium_value": "Senior + Peer", "enterprise_value": "Architect + Peer", "is_highlighted": False},
            {"feature_name": "Uptime Guarantee", "standard_value": "99.5%", "premium_value": "99.9%", "enterprise_value": "99.99%", "is_highlighted": True},
            {"feature_name": "Support Channels", "standard_value": "Email", "premium_value": "Email + Slack", "enterprise_value": "Email + Slack + Phone", "is_highlighted": False},
            {"feature_name": "Quarterly Business Review", "standard_value": "—", "premium_value": "—", "enterprise_value": "✓ Included", "is_highlighted": True},
        ]
        for i, r in enumerate(rows):
            obj, created = ServiceComparisonRow.objects.get_or_create(
                service=service, feature_name=r["feature_name"],
                defaults={**r, "order": i + 1},
            )
        self.stdout.write(f"  ✅ Service Comparison Rows: {len(rows)} created/updated")

    def _seed_service_client_logos(self, service):
        clients = [
            {"client_name": "TechCorp Global", "client_url": "https://techcorp.example.com"},
            {"client_name": "FinServe Banking", "client_url": ""},
            {"client_name": "HealthPlus Medical", "client_url": "https://healthplus.example.com"},
            {"client_name": "EduLearn Platform", "client_url": ""},
            {"client_name": "RetailMax Group", "client_url": "https://retailmax.example.com"},
            {"client_name": "LogiTrans Logistics", "client_url": ""},
        ]
        for i, c in enumerate(clients):
            obj, created = ServiceClientLogo.objects.get_or_create(
                service=service, client_name=c["client_name"],
                defaults={**c, "order": i + 1},
            )
        self.stdout.write(f"  ✅ Service Client Logos: {len(clients)} created/updated")

    def _seed_service_testimonials(self, service, testimonials):
        if not testimonials:
            self.stdout.write("  ⚠  Service Testimonials: skipped (no testimonials exist)")
            return
        for i, t in enumerate(testimonials[:3]):
            obj, created = ServiceTestimonial.objects.get_or_create(
                service=service, testimonial=t,
                defaults={"is_featured": (i == 0), "order": i + 1},
            )
        self.stdout.write(f"  ✅ Service Testimonials: {min(3, len(testimonials))} linked")

    def _seed_service_documents(self, service):
        docs = [
            {"title": "Technical Datasheet", "description": "Detailed technical specifications, architecture overview, and technology stack.", "document_type": "datasheet"},
            {"title": "ROI Whitepaper", "description": "In-depth analysis of return on investment, cost savings, and efficiency gains for enterprise clients.", "document_type": "whitepaper"},
            {"title": "Enterprise SLA Agreement", "description": "Full service-level agreement document outlining guarantees, penalties, and support terms.", "document_type": "specification"},
        ]
        for i, d in enumerate(docs):
            obj, created = ServiceDocument.objects.get_or_create(
                service=service, title=d["title"],
                defaults={**d, "is_public": True, "order": i + 1},
            )
        self.stdout.write(f"  ✅ Service Documents: {len(docs)} created/updated")

    def _seed_service_slas(self, service):
        slas = [
            {"guarantee_name": "Uptime Guarantee", "value": "99.99%", "description": "Financially backed uptime SLA with automatic service credits for any breach below the guaranteed threshold.", "icon": "lucide:shield-check"},
            {"guarantee_name": "Response Time", "value": "< 1 hour", "description": "Critical incidents acknowledged within 60 minutes. Non-critical issues within 4 business hours.", "icon": "lucide:timer"},
            {"guarantee_name": "Resolution Time", "value": "< 8 hours", "description": "Target resolution for P1 incidents. Includes root cause analysis delivered within 48 hours.", "icon": "lucide:wrench"},
            {"guarantee_name": "Data Security", "value": "SOC 2 & ISO 27001", "description": "All data encrypted at rest and in transit. Annual penetration testing and continuous vulnerability scanning.", "icon": "lucide:lock"},
        ]
        for i, s in enumerate(slas):
            obj, created = ServiceSLA.objects.get_or_create(
                service=service, guarantee_name=s["guarantee_name"],
                defaults={**s, "order": i + 1},
            )
        self.stdout.write(f"  ✅ Service SLAs: {len(slas)} created/updated")

    # ──────────────────────────────────────────────────────────────────────
    # SUPPORT TICKETS
    # ──────────────────────────────────────────────────────────────────────

    def _seed_support_tickets(self, admin_user, services):
        tickets = [
            {"title": "API rate limiting configuration needed", "description": "We're hitting rate limits on the v2/search endpoint during peak hours (9-11 AM EST). Need guidance on configuring burst limits.", "ticket_type": "technical_support", "status": "in_progress", "priority": "high"},
            {"title": "Request for custom SSO integration", "description": "Our enterprise client requires SAML-based SSO with Azure AD. We need an architecture review and implementation estimate.", "ticket_type": "project_request", "status": "open", "priority": "normal"},
            {"title": "Dashboard loading performance issue", "description": "The analytics dashboard takes 12+ seconds to load when filtering by date range > 3 months. Suspect unoptimized queries.", "ticket_type": "bug_report", "status": "open", "priority": "high"},
            {"title": "Partnership inquiry — AI healthcare solutions", "description": "We're a healthcare SaaS company looking to integrate your NLP capabilities for medical document processing. Interested in a strategic partnership.", "ticket_type": "partnership", "status": "open", "priority": "urgent"},
            {"title": "Mobile app dark mode not working on Android 14", "description": "Users on Android 14 report that dark mode toggle has no effect. iOS dark mode works correctly. Need investigation and fix.", "ticket_type": "bug_report", "status": "in_progress", "priority": "normal"},
            {"title": "General inquiry about enterprise pricing", "description": "We're evaluating your platform for a team of 50+ engineers. Would like to understand enterprise tier pricing and volume discounts.", "ticket_type": "general_inquiry", "status": "waiting_admin", "priority": "normal"},
        ]
        for t in tickets:
            slug_base = slugify(t["title"])[:240]
            slug = slug_base
            counter = 1
            while SupportTicket.objects.filter(slug=slug).exists():
                slug = f"{slug_base[:230]}-{counter}"
                counter += 1
            obj, created = SupportTicket.objects.get_or_create(
                slug=slug,
                defaults={
                    **t,
                    "guest_email": f"client-{random.randint(1000, 9999)}@example.com",
                    "assigned_to": admin_user,
                },
            )
            if created and services:
                obj.related_service = random.choice(services)
                obj.save(update_fields=["related_service"])
            self.stdout.write(f"  {'✅' if created else '⏭ '} Support Ticket: {obj.title}")
