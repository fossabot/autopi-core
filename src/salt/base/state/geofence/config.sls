
geofence-settings-configured:
 file.managed:
   - name: /opt/autopi/geofence/settings.yaml
   - source: {{ salt['pillar.get']('cloud_api:url')|replace("https://", "https+token://{:s}@".format(salt['pillar.get']('cloud_api:auth_token'))) }}/dongle/{{ salt['grains.get']('id') }}/salt/geofence?format=yaml
   - source_hash: {{ salt['pillar.get']('cloud_api:url')|replace("https://", "https+token://{:s}@".format(salt['pillar.get']('cloud_api:auth_token'))) }}/dongle/{{ salt['grains.get']('id') }}/salt/geofence?format=sha1sum
   - makedirs: true

geofence-settings-loaded:
  module.run:
    - name: tracking.load_geofences
    - require:
      - file: geofence-settings-configured
    - onchanges:
      - file: geofence-settings-configured