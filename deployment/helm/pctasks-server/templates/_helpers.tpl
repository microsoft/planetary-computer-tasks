{{/*
Expand the name of the chart.
*/}}
{{- define "pctasks.name" -}}
{{- default .Chart.Name .Values.pctasks.server.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "pctasks.fullname" -}}
{{- if .Values.pctasks.server.fullnameOverride }}
{{- .Values.pctasks.server.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.pctasks.server.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "pctasks.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "pctasks.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pctasks.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "pctasks.labels" -}}
helm.sh/chart: {{ include "pctasks.chart" . }}
{{ include "pctasks.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "pctasks.serviceAccountName" -}}
{{- if .Values.pctasks.server.serviceAccount.create }}
{{- default (include "pctasks.fullname" .) .Values.pctasks.server.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.pctasks.server.serviceAccount.name }}
{{- end }}
{{- end }}