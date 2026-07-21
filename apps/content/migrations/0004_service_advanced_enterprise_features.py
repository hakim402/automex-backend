# Generated manually for advanced service enterprise features

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0003_enhance_service_enterprise_features'),
        ('core', '0001_initial'),
    ]

    operations = [
        # ── tech_stack_grouped on Service ─────────────────────────────────────
        migrations.AddField(
            model_name='service',
            name='tech_stack_grouped',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Structured technology groups for display, e.g. {"Frontend": ["React"], "Backend": ["Django"]}.',
                verbose_name='grouped tech stack',
            ),
        ),
        # ── is_prominent on FAQ ───────────────────────────────────────────────
        migrations.AddField(
            model_name='faq',
            name='is_prominent',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='If True, this FAQ is shown in the hero/above-fold area rather than at the bottom of the page.',
                verbose_name='prominent',
            ),
        ),
        # ── ServiceProcessStep ────────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceProcessStep',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('custom_title', models.CharField(
                    blank=True,
                    help_text='Override the global process step title for this service.',
                    max_length=150,
                    verbose_name='custom title',
                )),
                ('custom_description', models.TextField(
                    blank=True,
                    help_text='Override the global process step description for this service.',
                    verbose_name='custom description',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='process_steps',
                    to='content.service',
                    verbose_name='service',
                )),
                ('process_step', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='service_links',
                    to='content.processstep',
                    verbose_name='process step',
                )),
            ],
            options={
                'verbose_name': 'service process step',
                'verbose_name_plural': 'service process steps',
                'ordering': ['order'],
            },
        ),
        migrations.AddConstraint(
            model_name='serviceprocessstep',
            constraint=models.UniqueConstraint(
                fields=('service', 'process_step'),
                name='uq_service_process_step',
            ),
        ),
        migrations.AddIndex(
            model_name='serviceprocessstep',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_svcprocstep_service_order',
            ),
        ),
        # ── ServiceDeliverable ────────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceDeliverable',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('title', models.CharField(max_length=200, verbose_name='title')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('icon', models.CharField(
                    blank=True,
                    help_text="Icon identifier for the frontend, e.g. 'lucide:file-code'.",
                    max_length=100,
                    verbose_name='icon',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='deliverables',
                    to='content.service',
                    verbose_name='service',
                )),
            ],
            options={
                'verbose_name': 'service deliverable',
                'verbose_name_plural': 'service deliverables',
                'ordering': ['order'],
            },
        ),
        migrations.AddIndex(
            model_name='servicedeliverable',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_svcdeliverable_service_order',
            ),
        ),
        # ── ServiceAddOn ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceAddOn',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('price', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text="Indicative price for this add-on. Leave blank for 'on request'.",
                    max_digits=10,
                    null=True,
                    verbose_name='price',
                )),
                ('is_included_in_enterprise', models.BooleanField(
                    default=False,
                    help_text='If True, this add-on is bundled with the enterprise tier at no extra cost.',
                    verbose_name='included in enterprise',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='add_ons',
                    to='content.service',
                    verbose_name='service',
                )),
            ],
            options={
                'verbose_name': 'service add-on',
                'verbose_name_plural': 'service add-ons',
                'ordering': ['order'],
            },
        ),
        migrations.AddIndex(
            model_name='serviceaddon',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_svcaddon_service_order',
            ),
        ),
        # ── ServiceComparisonRow ──────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceComparisonRow',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('feature_name', models.CharField(
                    help_text='The feature or capability being compared.',
                    max_length=200,
                    verbose_name='feature name',
                )),
                ('standard_value', models.CharField(
                    blank=True,
                    help_text="Value shown in the Standard column, e.g. '5 users', '✓', '—'.",
                    max_length=100,
                    verbose_name='standard',
                )),
                ('premium_value', models.CharField(
                    blank=True,
                    help_text='Value shown in the Premium column.',
                    max_length=100,
                    verbose_name='premium',
                )),
                ('enterprise_value', models.CharField(
                    blank=True,
                    help_text='Value shown in the Enterprise column.',
                    max_length=100,
                    verbose_name='enterprise',
                )),
                ('is_highlighted', models.BooleanField(
                    default=False,
                    help_text='If True, this row is visually emphasized on the frontend.',
                    verbose_name='highlighted',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='comparison_rows',
                    to='content.service',
                    verbose_name='service',
                )),
            ],
            options={
                'verbose_name': 'service comparison row',
                'verbose_name_plural': 'service comparison rows',
                'ordering': ['order'],
            },
        ),
        migrations.AddIndex(
            model_name='servicecomparisonrow',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_svccomparison_service_order',
            ),
        ),
        # ── ServiceClientLogo ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceClientLogo',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('client_name', models.CharField(
                    blank=True,
                    help_text='Displayed on hover or as alt text for the logo.',
                    max_length=200,
                    verbose_name='client name',
                )),
                ('client_url', models.URLField(
                    blank=True,
                    help_text="Optional link to the client's website.",
                    max_length=500,
                    verbose_name='client URL',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='client_logos',
                    to='content.service',
                    verbose_name='service',
                )),
                ('logo', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='core.mediaasset',
                    verbose_name='logo',
                )),
            ],
            options={
                'verbose_name': 'service client logo',
                'verbose_name_plural': 'service client logos',
                'ordering': ['order'],
            },
        ),
        migrations.AddIndex(
            model_name='serviceclientlogo',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_svcclientlogo_service_order',
            ),
        ),
        # ── ServiceTestimonial ────────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceTestimonial',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('is_featured', models.BooleanField(
                    db_index=True,
                    default=False,
                    help_text="Pin this testimonial to the top of the service's testimonial section.",
                    verbose_name='featured',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='service_testimonials',
                    to='content.service',
                    verbose_name='service',
                )),
                ('testimonial', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='service_links',
                    to='content.testimonial',
                    verbose_name='testimonial',
                )),
            ],
            options={
                'verbose_name': 'service testimonial',
                'verbose_name_plural': 'service testimonials',
                'ordering': ['-is_featured', 'order'],
            },
        ),
        migrations.AddConstraint(
            model_name='servicetestimonial',
            constraint=models.UniqueConstraint(
                fields=('service', 'testimonial'),
                name='uq_service_testimonial',
            ),
        ),
        migrations.AddIndex(
            model_name='servicetestimonial',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_svctestimonial_service_order',
            ),
        ),
        # ── ServiceDocument ───────────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceDocument',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('document_type', models.CharField(
                    choices=[
                        ('datasheet', 'Datasheet'),
                        ('whitepaper', 'Whitepaper'),
                        ('case_study', 'Case Study'),
                        ('specification', 'Specification'),
                        ('proposal', 'Proposal Template'),
                        ('other', 'Other'),
                    ],
                    db_index=True,
                    default='datasheet',
                    max_length=20,
                    verbose_name='document type',
                )),
                ('is_public', models.BooleanField(
                    default=True,
                    help_text='If False, only authenticated users can download.',
                    verbose_name='public download',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='content.service',
                    verbose_name='service',
                )),
                ('file', models.ForeignKey(
                    blank=True,
                    help_text='Upload the document to the media library, then link it here.',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='core.mediaasset',
                    verbose_name='file',
                )),
            ],
            options={
                'verbose_name': 'service document',
                'verbose_name_plural': 'service documents',
                'ordering': ['order'],
            },
        ),
        migrations.AddIndex(
            model_name='servicedocument',
            index=models.Index(
                fields=['service', 'document_type'],
                name='idx_svcdocument_service_type',
            ),
        ),
        # ── ServiceSLA ────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='ServiceSLA',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('guarantee_name', models.CharField(
                    help_text="e.g. 'Uptime Guarantee', 'Response Time SLA', '24/7 Support'.",
                    max_length=200,
                    verbose_name='guarantee name',
                )),
                ('value', models.CharField(
                    help_text="e.g. '99.9%', '< 4 hours', 'Always available'.",
                    max_length=100,
                    verbose_name='value',
                )),
                ('description', models.TextField(
                    blank=True,
                    help_text='Detailed explanation of this SLA guarantee.',
                    verbose_name='description',
                )),
                ('icon', models.CharField(
                    blank=True,
                    help_text="Icon identifier for the frontend, e.g. 'lucide:shield-check'.",
                    max_length=100,
                    verbose_name='icon',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='slas',
                    to='content.service',
                    verbose_name='service',
                )),
            ],
            options={
                'verbose_name': 'service SLA',
                'verbose_name_plural': 'service SLAs',
                'ordering': ['order'],
            },
        ),
        migrations.AddIndex(
            model_name='servicesla',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_svcsla_service_order',
            ),
        ),
    ]
