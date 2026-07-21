# Generated manually for enterprise service enhancements

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        # ── New fields on Service ─────────────────────────────────────────────
        migrations.AddField(
            model_name='service',
            name='service_level',
            field=models.CharField(
                choices=[('standard', 'Standard'), ('premium', 'Premium'), ('enterprise', 'Enterprise')],
                db_index=True,
                default='standard',
                help_text='Tier used for filtering and pricing display.',
                max_length=20,
                verbose_name='service level',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='is_enterprise',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Flag for dedicated enterprise-grade service pages.',
                verbose_name='enterprise service',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='thumbnail_image',
            field=models.ForeignKey(
                blank=True,
                help_text='Small image used in cards, grids, and listing pages.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='core.mediaasset',
                verbose_name='thumbnail image',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='video_presentation',
            field=models.ForeignKey(
                blank=True,
                help_text='Service overview video or demo reel.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='core.mediaasset',
                verbose_name='video presentation',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='brochure',
            field=models.ForeignKey(
                blank=True,
                help_text='Downloadable PDF brochure or service datasheet.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='core.mediaasset',
                verbose_name='brochure / datasheet',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='pricing_model',
            field=models.CharField(
                blank=True,
                choices=[
                    ('fixed', 'Fixed Price'),
                    ('hourly', 'Hourly Rate'),
                    ('quote', 'Custom Quote'),
                    ('subscription', 'Subscription'),
                    ('retainer', 'Retainer'),
                ],
                default='quote',
                max_length=20,
                verbose_name='pricing model',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='starting_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Indicative starting price for display purposes.',
                max_digits=10,
                null=True,
                verbose_name='starting price',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='currency',
            field=models.CharField(
                blank=True,
                default='USD',
                help_text="ISO 4217 currency code, e.g. 'USD', 'EUR'.",
                max_length=3,
                verbose_name='currency',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='delivery_time_estimate',
            field=models.CharField(
                blank=True,
                help_text="e.g. '4-6 weeks', '2-3 months'. Shown on the service page.",
                max_length=100,
                verbose_name='delivery time estimate',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='team_size_range',
            field=models.CharField(
                blank=True,
                help_text="e.g. '3-8 engineers', 'Dedicated team of 5+'.",
                max_length=100,
                verbose_name='team size range',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='key_metrics',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Structured metrics for display, e.g. {"projects_delivered": 150, "client_satisfaction": 98}.',
                verbose_name='key metrics',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='enterprise_features',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='List of enterprise-tier capabilities, e.g. ["Dedicated team", "SLA guarantee"].',
                verbose_name='enterprise features',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='related_services',
            field=models.ManyToManyField(
                blank=True,
                help_text="Cross-linked services shown as 'You might also need'.",
                related_name='related_to',
                to='content.service',
                verbose_name='related services',
            ),
        ),
        # ── New translated fields on ServiceTranslation ───────────────────────
        migrations.AddField(
            model_name='servicetranslation',
            name='cta_text',
            field=models.CharField(
                blank=True,
                help_text="Call-to-action button label, e.g. 'Get a Quote', 'Start Your Project'.",
                max_length=100,
                verbose_name='CTA text',
            ),
        ),
        migrations.AddField(
            model_name='servicetranslation',
            name='cta_url',
            field=models.URLField(
                blank=True,
                help_text='Override the CTA destination per language. Leave blank for default contact form.',
                max_length=500,
                verbose_name='CTA URL',
            ),
        ),
        # ── Update hero_image help_text ───────────────────────────────────────
        migrations.AlterField(
            model_name='service',
            name='hero_image',
            field=models.ForeignKey(
                blank=True,
                help_text='Main hero image (used as fallback if no gallery images are set).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='core.mediaasset',
                verbose_name='primary hero image',
            ),
        ),
        # ── Update icon help_text ─────────────────────────────────────────────
        migrations.AlterField(
            model_name='service',
            name='icon',
            field=models.CharField(
                blank=True,
                help_text="Icon identifier used by the frontend, e.g. 'lucide:code'.",
                max_length=100,
                verbose_name='icon',
            ),
        ),
        # ── Indexes on Service ────────────────────────────────────────────────
        migrations.AddIndex(
            model_name='service',
            index=models.Index(
                fields=['service_level', 'is_enterprise'],
                name='idx_service_level_enterprise',
            ),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(
                fields=['is_featured', 'status'],
                name='idx_service_featured_status',
            ),
        ),
        # ── Create ServiceHeroImage model ─────────────────────────────────────
        migrations.CreateModel(
            name='ServiceHeroImage',
            fields=[
                ('id', models.UUIDField(db_index=True, default=None, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='display order')),
                ('caption', models.CharField(
                    blank=True,
                    help_text='Optional caption or overlay text displayed on the hero image.',
                    max_length=255,
                    verbose_name='caption',
                )),
                ('is_cover', models.BooleanField(
                    default=False,
                    help_text='If set, this image is used as the primary cover/first slide.',
                    verbose_name='cover image',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='hero_images',
                    to='content.service',
                    verbose_name='service',
                )),
                ('image', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to='core.mediaasset',
                    verbose_name='image',
                )),
            ],
            options={
                'verbose_name': 'service hero image',
                'verbose_name_plural': 'service hero images',
                'ordering': ['order'],
            },
        ),
        migrations.AddIndex(
            model_name='serviceheroimage',
            index=models.Index(
                fields=['service', 'order'],
                name='idx_servicehero_service_order',
            ),
        ),
    ]
