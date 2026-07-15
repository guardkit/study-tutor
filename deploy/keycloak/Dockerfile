# Keycloak 26.6 with optimized postgres build baked in
# (KC-D1: pre-build optimization for --optimized start mode)
FROM quay.io/keycloak/keycloak:26.0.7

# Bake the optimized build for postgres + health endpoint
RUN /opt/keycloak/bin/kc.sh build --db=postgres --health-enabled=true
