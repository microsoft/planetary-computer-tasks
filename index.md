---
layout: default
---

# Getting Started

{{ site.description }}

## Helm Repository

You can add this repository to your local helm configuration as follows :

```console
$ helm repo add {{ site.repo_name }} {{ site.url }}
$ helm repo update
```

### Charts

{% comment %}[0] and [1] below represent key and value{% endcomment %}
{% for helm_chart in site.data.index.entries %}
{% assign title = helm_chart[0] %}
{% assign all_charts = helm_chart[1] | sort: 'created' | reverse %}
{% assign latest_chart = all_charts[0] %}

<h3>
  {% if latest_chart.icon %}
  <img src="{{ latest_chart.icon }}" style="height:1.2em;vertical-align: text-top;" />
  {% endif %}
  {{ title }}
</h3>

[Home]({{ latest_chart.home }}) \| [Source]({{ latest_chart.sources[0] }})

{{ latest_chart.description }}

```console
$ helm install --version {{ latest_chart.version }} myrelease {{ site.repo_name }}/{{ latest_chart.name }}
```

| Chart |{% for dep in latest_chart.dependencies %} {{ dep.name | capitalize }} |{% endfor %} App | Date |
| - | - | - |{% for dep in latest_chart.dependencies %} - |{% endfor %}
{% for chart in all_charts -%}
| [{{ chart.name }}-{{ chart.version }}]({{ chart.urls[0] }}) |{% for dep in chart.dependencies %} {{ dep.version | capitalize }} |{% endfor %} {{ chart.appVersion }} | {{ chart.created | date_to_long_string }} |
{% endfor -%}

{% endfor %}

## Script packages

{% for package_type in site.data.pkg-index.packages %}
{% assign title = package_type[0] %}
{% assign all_versions = package_type[1] | sort: 'created' | reverse %}
{% assign latest_version = all_versions[0] %}

### {{ title }}

{{ latest_version.description }}

Last updated: {{ latest_version.created | date_to_long_string }}

| Package | Version | Date |
|---------|---------|------|
{% for package in all_versions | sort: 'created' | reverse -%}
| [{{ package.name }}]({{ package.url }}) | {{ package.version }} | {{ package.created | date_to_long_string }} |
{% endfor %}
{% endfor %}
