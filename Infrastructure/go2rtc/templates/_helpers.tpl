{{- define "go2rtc.labels" -}}
app.kubernetes.io/name: go2rtc
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "go2rtc.selectorLabels" -}}
app.kubernetes.io/name: go2rtc
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
