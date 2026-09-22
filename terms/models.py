from django.db import models

class StaticPage(models.Model):

    title = models.CharField(max_length=200)

    slug = models.SlugField(unique=True)

    html_content = models.TextField()
