"""
apps/core/management/commands/seed_demo_data.py
─────────────────────────────────────────────────────
Seeds a full, realistic demo catalog matching the AUTOMEX MVP doc: all 7
services, technologies, industries, process steps, FAQs, case studies,
blog content, team, testimonials, booking availability, calculator rules,
and AI knowledge entries.

IMPORTANT — case studies, team members, and testimonials below are
clearly-fictional placeholder content (generic names, no real client
claims) meant to demonstrate the CMS working end-to-end. Replace them with
real content before this goes live — this command prints a reminder every
time it runs.

Idempotent: uses get_or_create/update_or_create keyed by slug, so running
this multiple times updates rather than duplicates.

Usage:
    python manage.py seed_demo_data
"""
from __future__ import annotations

from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.assistant.models import AIKnowledgeEntry
from apps.content.models import (
    FAQ,
    BlogCategory,
    BlogPost,
    BlogTag,
    CaseStudy,
    Industry,
    ProcessStep,
    Service,
    ServiceCategory,
    TeamMember,
    Technology,
    Testimonial,
)
from apps.core.models import PublishableModel
from apps.crm.models import AvailabilitySlot, ComplexityTier, CostCalculatorRule


class Command(BaseCommand):
    help = "Seed a full realistic demo catalog (services, case studies, blog, team, ...) for local dev/testing."

    def handle(self, *args, **options) -> None:
        self.stdout.write(self.style.WARNING(
            "Seeding DEMO/PLACEHOLDER content. Case studies, team members, and "
            "testimonials are fictional examples — replace with real content "
            "before production launch.\n"
        ))

        categories = self._seed_service_categories()
        technologies = self._seed_technologies()
        industries = self._seed_industries()
        self._seed_process_steps()
        services = self._seed_services(categories, technologies, industries)
        self._seed_faqs(services)
        self._seed_ai_knowledge_entries(services)
        self._seed_case_studies(services, technologies, industries)
        self._seed_blog()
        self._seed_team()
        self._seed_testimonials(services)
        self._seed_availability_slots()
        self._seed_calculator_rules(services)

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully."))

    # ──────────────────────────────────────────────────────────────────────
    # TAXONOMY
    # ──────────────────────────────────────────────────────────────────────

    def _seed_service_categories(self) -> dict[str, ServiceCategory]:
        names = [
            "Custom Software Development", "Artificial Intelligence",
            "Data Engineering & Analytics", "ERP & CRM Solutions",
            "Cloud & DevOps", "UI/UX Design", "IT Staff Augmentation",
        ]
        categories = {}
        for order, name in enumerate(names):
            slug = _slugify(name)
            category, _created = ServiceCategory.objects.get_or_create(
                slug=slug, defaults={"name": name, "order": order},
            )
            categories[name] = category
        self.stdout.write(f"  ServiceCategory: {len(categories)}")
        return categories

    def _seed_technologies(self) -> dict[str, Technology]:
        rows = [
            ("Next.js", "frontend"), ("TypeScript", "frontend"),
            ("Python", "backend"), ("Django + DRF", "backend"),
            ("PostgreSQL", "database"),
            ("Hostinger VPS", "cloud"), ("Docker", "cloud"),
            ("Groq AI", "ai"),
            ("Odoo", "enterprise"), ("Microsoft Dynamics 365", "enterprise"),
            ("Kubernetes", "devops"), ("GitHub Actions", "devops"),
        ]
        technologies = {}
        for order, (name, category) in enumerate(rows):
            slug = _slugify(name)
            tech, _created = Technology.objects.get_or_create(
                slug=slug, defaults={"name": name, "category": category, "order": order},
            )
            technologies[name] = tech
        self.stdout.write(f"  Technology: {len(technologies)}")
        return technologies

    def _seed_industries(self) -> dict[str, Industry]:
        names = [
            "Healthcare", "Finance", "Retail", "Manufacturing", "Logistics",
            "Government", "Education", "Real Estate", "E-Commerce", "SaaS",
        ]
        industries = {}
        for order, name in enumerate(names):
            slug = _slugify(name)
            industry = Industry.objects.filter(translations__slug=slug).first()
            if not industry:
                industry = Industry.objects.create(order=order)
                industry.set_current_language("en")
                industry.name = name
                industry.slug = slug
                industry.description = f"Technology solutions tailored for the {name.lower()} industry."
                industry.save()
            industries[name] = industry
        self.stdout.write(f"  Industry: {len(industries)}")
        return industries

    def _seed_process_steps(self) -> None:
        steps = [
            ("Discovery", "We start by understanding your business goals, users, and technical constraints."),
            ("Planning", "Scope, timeline, and architecture are mapped out before a line of code is written."),
            ("UI/UX Design", "Wireframes and interactive prototypes validate the experience before development."),
            ("Development", "Agile sprints deliver working software in short, reviewable increments."),
            ("Quality Assurance", "Automated and manual testing catch issues before they reach production."),
            ("Deployment", "Releases are automated, monitored, and reversible."),
            ("Maintenance & Support", "Ongoing support keeps your product secure, fast, and up to date."),
        ]
        for order, (title, description) in enumerate(steps):
            step = ProcessStep.objects.filter(translations__title=title).first()
            if not step:
                step = ProcessStep.objects.create(order=order)
                step.set_current_language("en")
                step.title = title
                step.description = description
                step.save()
        self.stdout.write(f"  ProcessStep: {len(steps)}")

    # ──────────────────────────────────────────────────────────────────────
    # SERVICES
    # ──────────────────────────────────────────────────────────────────────

    def _seed_services(self, categories, technologies, industries) -> dict[str, Service]:
        now = timezone.now()
        specs = [
            dict(
                name="Custom Software Development",
                short_description="Custom software tailored to your business requirements, from MVP to enterprise scale.",
                overview="We design and build custom software — enterprise applications, SaaS platforms, and MVPs — engineered to fit how your business actually works, not the other way around.",
                problems_we_solve="Off-the-shelf software doesn't fit your workflow.\nLegacy systems are slow to change and expensive to maintain.\nYou need a working product fast without cutting corners on quality.",
                features="Custom software & enterprise applications\nSaaS platform development\nMVP development\nAPI development & system integration\nSoftware modernization\nQuality assurance & testing",
                benefits="Launch faster with an MVP-first approach\nReduce long-term maintenance costs\nScale confidently on a modern architecture\nIntegrate cleanly with your existing systems",
                icon="lucide:code-2",
                is_featured=True,
                technologies=["Next.js", "TypeScript", "Python", "Django + DRF", "PostgreSQL"],
                industries=["SaaS", "Finance", "Retail"],
            ),
            dict(
                name="Artificial Intelligence",
                short_description="Intelligent applications that automate processes and improve decision-making.",
                overview="From AI chatbots to computer vision, we build AI-powered applications that plug into your existing workflows and start delivering value immediately.",
                problems_we_solve="Manual processes that don't scale with growth.\nCustomer support teams overwhelmed by repetitive questions.\nDecisions being made on gut feel instead of data.",
                features="AI applications & chatbots\nAI assistants\nWorkflow automation\nMachine learning & NLP\nComputer vision\nAI integration into existing systems",
                benefits="Automate repetitive work across support, sales, and ops\nMake faster, data-informed decisions\nOffer 24/7 intelligent customer interaction",
                icon="lucide:brain-circuit",
                is_featured=True,
                technologies=["Python", "Groq AI", "Django + DRF"],
                industries=["SaaS", "Healthcare", "E-Commerce"],
            ),
            dict(
                name="Data Engineering & Analytics",
                short_description="Transform business data into valuable insights with modern data infrastructure.",
                overview="We build the data pipelines and dashboards that turn scattered, siloed data into a single source of truth your team can actually act on.",
                problems_we_solve="Data lives in disconnected systems no one fully trusts.\nReporting takes days instead of minutes.\nLeadership lacks real-time visibility into the business.",
                features="Data engineering & ETL pipelines\nData warehousing\nBusiness intelligence dashboards\nAnalytics platforms\nReporting systems",
                benefits="Make decisions on real-time, trustworthy data\nReduce time spent manually compiling reports\nScale your data infrastructure as you grow",
                icon="lucide:bar-chart-3",
                is_featured=False,
                technologies=["Python", "PostgreSQL"],
                industries=["Finance", "Manufacturing", "Logistics"],
            ),
            dict(
                name="ERP & CRM Solutions",
                short_description="Implement enterprise resource planning and customer relationship management systems.",
                overview="We implement and customize Odoo and Microsoft Dynamics 365 across CRM, sales, HR, finance, inventory, and manufacturing modules.",
                problems_we_solve="Sales, finance, and operations run on disconnected spreadsheets.\nYour current ERP/CRM doesn't fit how your team actually works.\nGrowth is outpacing your current systems.",
                features="CRM & sales pipeline management\nHR & finance modules\nInventory & procurement\nManufacturing operations\nCustomer support tooling",
                benefits="One source of truth across departments\nReduce manual data entry and reconciliation\nScale operations without adding headcount",
                icon="lucide:building-2",
                is_featured=False,
                technologies=["Odoo", "Microsoft Dynamics 365", "PostgreSQL"],
                industries=["Manufacturing", "Retail", "Logistics"],
            ),
            dict(
                name="Cloud & DevOps",
                short_description="Deploy secure and scalable cloud infrastructure with modern DevOps practices.",
                overview="We design cloud architecture and CI/CD pipelines that let your team ship confidently, with infrastructure that scales with demand instead of against it.",
                problems_we_solve="Deployments are manual, slow, and risky.\nInfrastructure costs are unpredictable and hard to reason about.\nOutages take too long to detect and resolve.",
                features="Cloud architecture (AWS, Azure)\nDocker & Kubernetes\nCI/CD pipelines\nInfrastructure automation\nMonitoring & alerting\nDevOps consulting",
                benefits="Ship faster with automated, reliable deployments\nReduce infrastructure costs through right-sizing\nCatch issues before customers do",
                icon="lucide:cloud-cog",
                is_featured=True,
                technologies=["Docker", "Kubernetes", "GitHub Actions", "Hostinger VPS"],
                industries=["SaaS", "Government", "Education"],
            ),
            dict(
                name="UI/UX Design",
                short_description="Create intuitive user experiences with modern interface design.",
                overview="From research to interactive prototypes, we design digital products people actually enjoy using — and that convert.",
                problems_we_solve="Users abandon your product before completing key actions.\nYour interface looks dated next to competitors.\nDesign and engineering are out of sync.",
                features="UX research & user flows\nWireframes & interactive prototypes\nUI design systems\nMobile & web design",
                benefits="Increase conversion with a tested user experience\nShip a consistent design system across products\nReduce engineering rework from late-stage design changes",
                icon="lucide:palette",
                is_featured=False,
                technologies=["Next.js", "TypeScript"],
                industries=["Retail", "E-Commerce", "Real Estate"],
            ),
            dict(
                name="IT Staff Augmentation",
                short_description="Experienced software professionals embedded directly in your team.",
                overview="Frontend, backend, full-stack, mobile, DevOps, QA, AI, design, and PM talent — vetted and embedded in your existing team, not a black-box outsourced squad.",
                problems_we_solve="Hiring takes months you don't have.\nYou need specialized skills for a single project, not a permanent hire.\nYour team is stretched too thin to hit the deadline.",
                features="Frontend & backend developers\nFull stack & mobile developers\nDevOps & QA engineers\nAI engineers\nUI/UX designers\nProject managers",
                benefits="Scale your team up or down as project needs change\nFill specialized skill gaps quickly\nKeep full visibility and control over the work",
                icon="lucide:users",
                is_featured=False,
                technologies=["Python", "Django + DRF", "Next.js", "TypeScript"],
                industries=["SaaS", "Finance", "Healthcare"],
            ),
        ]

        services = {}
        for order, spec in enumerate(specs):
            slug = _slugify(spec["name"])
            service = Service.objects.filter(translations__slug=slug).first()
            if not service:
                service = Service.objects.create(
                    category=categories.get(spec["name"]),
                    icon=spec["icon"],
                    is_featured=spec["is_featured"],
                    order=order,
                    status=PublishableModel.Status.PUBLISHED,
                    published_at=now,
                )
                service.set_current_language("en")
                service.name = spec["name"]
                service.slug = slug
                service.short_description = spec["short_description"]
                service.overview = spec["overview"]
                service.problems_we_solve = spec["problems_we_solve"]
                service.features = spec["features"]
                service.benefits = spec["benefits"]
                # Truncate meta_title to avoid exceeding max_length
                service.meta_title = _truncate_meta_title(spec["name"], suffix=" | AUTOMEX")
                service.meta_description = spec["short_description"]
                service.save()

                service.technologies.set([technologies[t] for t in spec["technologies"] if t in technologies])
                service.industries.set([industries[i] for i in spec["industries"] if i in industries])

            services[spec["name"]] = service

        self.stdout.write(f"  Service: {len(services)}")
        return services

    # ──────────────────────────────────────────────────────────────────────
    # FAQ
    # ──────────────────────────────────────────────────────────────────────

    def _seed_faqs(self, services: dict[str, Service]) -> None:
        rows = [
            ("How long does development take?", "Timelines vary by scope — a focused MVP typically takes 6-10 weeks; larger enterprise builds are scoped individually during discovery.", "process"),
            ("How much does a software project cost?", "Cost depends on complexity, timeline, and team size. Use our cost calculator for an instant estimate, or book a free consultation for a detailed quote.", "pricing"),
            ("Do you provide post-launch support?", "Yes — every engagement includes a maintenance & support phase, and we offer ongoing retainers for ongoing feature work and monitoring.", "general"),
            ("Can you modernize existing software?", "Yes, software modernization is one of our core Custom Software Development offerings — from incremental refactors to full re-platforming.", "general"),
            ("Do you sign NDAs?", "Yes, we're happy to sign an NDA before any detailed discovery discussion.", "general"),
            ("What technologies do you use?", "Our core stack includes Next.js, TypeScript, Python, Django + DRF, and PostgreSQL, deployed on Docker-based cloud infrastructure — see our Technologies page for the full list.", "general"),
            ("Can you build AI-powered applications?", "Yes — AI chatbots, assistants, workflow automation, and custom ML/NLP/computer vision applications are a core service.", "general"),
            ("Do you provide dedicated development teams?", "Yes, through our IT Staff Augmentation service — vetted frontend, backend, mobile, DevOps, QA, AI, and design talent embedded in your team.", "general"),
        ]
        for order, (question, answer, category) in enumerate(rows):
            faq = FAQ.objects.filter(service=None, translations__question=question).first()
            if not faq:
                faq = FAQ.objects.create(service=None, category=category, order=order)
                faq.set_current_language("en")
                faq.question = question
                faq.answer = answer
                faq.save()
        self.stdout.write(f"  FAQ (global): {len(rows)}")

    def _seed_ai_knowledge_entries(self, services: dict[str, Service]) -> None:
        """Grounds the AI Sales Assistant — same content as the global FAQ, plus a couple extras."""
        rows = [
            ("How long does development take?", "Timelines vary by scope — a focused MVP typically takes 6-10 weeks; larger enterprise builds are scoped individually during discovery.", None),
            ("How much does a software project cost?", "Cost depends on complexity, timeline, and team size. Recommend the visitor try the cost calculator or book a free consultation for a detailed quote.", None),
            ("Do you sign NDAs?", "Yes, AUTOMEX signs NDAs before any detailed discovery discussion.", None),
            ("What technologies does AUTOMEX use?", "Next.js, TypeScript, Python, Django + DRF, PostgreSQL, and Docker-based cloud infrastructure.", None),
            ("Does AUTOMEX build AI-powered applications?", "Yes — AI chatbots, assistants, workflow automation, and custom ML/NLP/computer vision applications.", "Artificial Intelligence"),
            ("Does AUTOMEX provide dedicated development teams?", "Yes, through IT Staff Augmentation — vetted developers, designers, and engineers embedded directly in the client's team.", "IT Staff Augmentation"),
        ]
        count = 0
        for question, answer, service_name in rows:
            _entry, created = AIKnowledgeEntry.objects.get_or_create(
                question=question,
                defaults=dict(answer=answer, related_service=services.get(service_name) if service_name else None),
            )
            count += 1
        self.stdout.write(f"  AIKnowledgeEntry: {count}")

    # ──────────────────────────────────────────────────────────────────────
    # CASE STUDIES (fictional demo clients — see module docstring)
    # ──────────────────────────────────────────────────────────────────────

    def _seed_case_studies(self, services, technologies, industries) -> None:
        now = timezone.now()
        specs = [
            dict(
                title="Meridian Health Group: Patient Portal Modernization",
                client_name="Meridian Health Group (demo client)",
                client_industry="Healthcare",
                overview="A legacy patient portal was rebuilt on a modern stack to support 5x the concurrent user load.",
                challenge="The existing portal couldn't handle appointment-booking traffic spikes and had no mobile experience.",
                solution="We re-platformed the portal on Django + DRF with a Next.js frontend, adding a booking system and real-time notifications.",
                results="Page load times dropped by 68%, mobile bookings increased 3x within the first quarter.",
                services=["Custom Software Development", "Cloud & DevOps"],
                technologies=["Next.js", "Django + DRF", "PostgreSQL", "Docker"],
                duration_weeks=14,
                is_featured=True,
            ),
            dict(
                title="Northwind Logistics: Real-Time Fleet Analytics",
                client_name="Northwind Logistics (demo client)",
                client_industry="Logistics",
                overview="A data platform consolidating fleet telemetry into a single real-time operations dashboard.",
                challenge="Fleet data was scattered across three vendor systems with no unified reporting.",
                solution="We built ETL pipelines consolidating all three data sources into a PostgreSQL warehouse with a live BI dashboard.",
                results="Dispatch decisions that took hours now take minutes; fuel cost reporting accuracy improved significantly.",
                services=["Data Engineering & Analytics"],
                technologies=["Python", "PostgreSQL"],
                duration_weeks=10,
                is_featured=True,
            ),
            dict(
                title="Vertex Retail Co.: AI-Powered Customer Support",
                client_name="Vertex Retail Co. (demo client)",
                client_industry="E-Commerce",
                overview="An AI assistant handling first-line customer support across a high-traffic e-commerce storefront.",
                challenge="A growing support ticket volume was outpacing the support team's capacity.",
                solution="We built an AI-powered chat assistant grounded in the client's product catalog and policies, escalating only complex cases to humans.",
                results="First-response time dropped from hours to seconds; the support team's ticket backlog was cut by more than half.",
                services=["Artificial Intelligence"],
                technologies=["Python", "Groq AI", "Django + DRF"],
                duration_weeks=8,
                is_featured=False,
            ),
        ]

        for order, spec in enumerate(specs):
            slug = _slugify(spec["title"])
            case_study = CaseStudy.objects.filter(translations__slug=slug).first()
            if not case_study:
                case_study = CaseStudy.objects.create(
                    client_name=spec["client_name"],
                    client_industry=industries.get(spec["client_industry"]),
                    project_duration_weeks=spec["duration_weeks"],
                    is_featured=spec["is_featured"],
                    order=order,
                    status=PublishableModel.Status.PUBLISHED,
                    published_at=now,
                )
                case_study.set_current_language("en")
                case_study.title = spec["title"]
                case_study.slug = slug
                case_study.overview = spec["overview"]
                case_study.challenge = spec["challenge"]
                case_study.solution = spec["solution"]
                case_study.results = spec["results"]
                # Truncate meta_title to avoid exceeding max_length
                case_study.meta_title = _truncate_meta_title(spec["title"], suffix=" | AUTOMEX Case Studies")
                case_study.meta_description = spec["overview"]
                case_study.save()

                case_study.related_services.set([services[s] for s in spec["services"] if s in services])
                case_study.technologies.set([technologies[t] for t in spec["technologies"] if t in technologies])

        self.stdout.write(f"  CaseStudy (demo/fictional): {len(specs)}")

    # ──────────────────────────────────────────────────────────────────────
    # BLOG
    # ──────────────────────────────────────────────────────────────────────

    def _seed_blog(self) -> None:
        category_names = ["Engineering", "AI & Data"]
        categories = {}
        for order, name in enumerate(category_names):
            slug = _slugify(name)
            category, _created = BlogCategory.objects.get_or_create(slug=slug, defaults={"name": name, "order": order})
            categories[name] = category

        tag_names = ["Django", "Next.js", "AI", "DevOps"]
        tags = {}
        for name in tag_names:
            slug = _slugify(name)
            tag, _created = BlogTag.objects.get_or_create(slug=slug, defaults={"name": name})
            tags[name] = tag

        posts = [
            dict(
                title="Why We Build on Django + DRF for Enterprise Backends",
                excerpt="A look at why Django's batteries-included philosophy pays off for complex, long-lived enterprise systems.",
                content="Django's mature ecosystem, built-in admin, and ORM let us focus engineering effort on business logic instead of reinventing infrastructure. Combined with Django REST Framework, it gives enterprise clients a maintainable, well-documented API surface from day one.",
                category="Engineering", tags=["Django", "DevOps"],
            ),
            dict(
                title="Grounding AI Assistants in Real Business Data",
                excerpt="How we ground conversational AI in a company's actual services and knowledge base instead of generic answers.",
                content="A generic LLM answer is rarely a useful business answer. We ground every AI assistant we build in the client's real, current content — services, FAQs, and policies — so answers stay accurate as the business changes.",
                category="AI & Data", tags=["AI"],
            ),
            dict(
                title="Shipping Faster with CI/CD on a Modest Budget",
                excerpt="You don't need a platform team to get reliable, automated deployments.",
                content="A well-configured GitHub Actions pipeline and a Dockerized app get most teams 90% of the deployment reliability of a much more complex setup, at a fraction of the operational overhead.",
                category="Engineering", tags=["DevOps", "Next.js"],
            ),
        ]

        for order, spec in enumerate(posts):
            slug = _slugify(spec["title"])
            post = BlogPost.objects.filter(translations__slug=slug).first()
            if not post:
                post = BlogPost.objects.create(
                    category=categories.get(spec["category"]),
                    status=PublishableModel.Status.PUBLISHED,
                    published_at=timezone.now(),
                    reading_time_minutes=4,
                )
                post.set_current_language("en")
                post.title = spec["title"]
                post.slug = slug
                post.excerpt = spec["excerpt"]
                post.content = spec["content"]
                # Truncate meta_title to avoid exceeding max_length
                post.meta_title = _truncate_meta_title(spec["title"], suffix=" | AUTOMEX Insights")
                post.meta_description = spec["excerpt"]
                post.save()
                post.tags.set([tags[t] for t in spec["tags"] if t in tags])

        self.stdout.write(f"  BlogPost: {len(posts)}")

    # ──────────────────────────────────────────────────────────────────────
    # TEAM (placeholder — see module docstring)
    # ──────────────────────────────────────────────────────────────────────

    def _seed_team(self) -> None:
        members = [
            ("Alex Morgan (placeholder)", "Founder & CEO", TeamMember.Department.MANAGEMENT, True),
            ("Sam Rivera (placeholder)", "Lead Backend Engineer", TeamMember.Department.ENGINEERING, False),
            ("Jordan Lee (placeholder)", "Lead AI Engineer", TeamMember.Department.AI, False),
            ("Casey Park (placeholder)", "Head of Design", TeamMember.Department.DESIGN, False),
        ]
        for order, (name, role, department, is_leadership) in enumerate(members):
            slug = _slugify(name)
            TeamMember.objects.get_or_create(
                slug=slug,
                defaults=dict(full_name=name, role_title=role, department=department, is_leadership=is_leadership, order=order),
            )
        self.stdout.write(f"  TeamMember (placeholder): {len(members)}")

    # ──────────────────────────────────────────────────────────────────────
    # TESTIMONIALS (placeholder — see module docstring)
    # ──────────────────────────────────────────────────────────────────────

    def _seed_testimonials(self, services: dict[str, Service]) -> None:
        rows = [
            ("Dana Whitfield (demo)", "VP of Operations", "Meridian Health Group (demo client)",
             "The team rebuilt our patient portal faster than we thought possible, without a single day of downtime.",
             "Custom Software Development"),
            ("Priya Nandan (demo)", "Head of Data", "Northwind Logistics (demo client)",
             "We finally have one dashboard the whole company trusts. That alone changed how we make decisions.",
             "Data Engineering & Analytics"),
            ("Marcus Boone (demo)", "Director of Support", "Vertex Retail Co. (demo client)",
             "Our support backlog dropped in half within weeks of launching the AI assistant.",
             "Artificial Intelligence"),
        ]
        for order, (client_name, role, company, quote, service_name) in enumerate(rows):
            Testimonial.objects.get_or_create(
                client_name=client_name, client_company=company,
                defaults=dict(
                    client_role=role, quote=quote, rating=5, order=order,
                    related_service=services.get(service_name),
                ),
            )
        self.stdout.write(f"  Testimonial (placeholder): {len(rows)}")

    # ──────────────────────────────────────────────────────────────────────
    # BOOKING & CALCULATOR
    # ──────────────────────────────────────────────────────────────────────

    def _seed_availability_slots(self) -> None:
        count = 0
        for weekday in range(0, 5):  # Monday–Friday
            _slot, created = AvailabilitySlot.objects.get_or_create(
                weekday=weekday, start_time=time(9, 0), end_time=time(17, 0),
                defaults={"timezone": "UTC", "max_bookings": 3},
            )
            count += 1
        self.stdout.write(f"  AvailabilitySlot: {count} (Mon-Fri, 9:00-17:00 UTC)")

    def _seed_calculator_rules(self, services: dict[str, Service]) -> None:
        tier_multipliers = {
            ComplexityTier.BASIC: (Decimal("5000"), Decimal("15000"), 2, 6),
            ComplexityTier.STANDARD: (Decimal("15000"), Decimal("40000"), 6, 12),
            ComplexityTier.ADVANCED: (Decimal("40000"), Decimal("90000"), 12, 20),
            ComplexityTier.ENTERPRISE: (Decimal("90000"), Decimal("250000"), 20, 40),
        }
        count = 0
        for service in services.values():
            for tier, (price_min, price_max, weeks_min, weeks_max) in tier_multipliers.items():
                _rule, created = CostCalculatorRule.objects.get_or_create(
                    service=service, complexity_tier=tier,
                    defaults=dict(
                        base_price_min=price_min, base_price_max=price_max,
                        estimated_duration_weeks_min=weeks_min, estimated_duration_weeks_max=weeks_max,
                    ),
                )
                count += 1
        self.stdout.write(f"  CostCalculatorRule: {count}")


# ─── Helpers ──────────────────────────────────────────────────────────────

def _slugify(value: str) -> str:
    import re
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _truncate_meta_title(title: str, suffix: str, max_len: int = 70) -> str:
    """Ensure meta_title + suffix does not exceed max_len (default 70)."""
    available = max_len - len(suffix)
    if available <= 0:
        # If suffix is longer than max_len, truncate suffix itself
        return suffix[:max_len]
    truncated_title = title[:available]
    return f"{truncated_title}{suffix}"