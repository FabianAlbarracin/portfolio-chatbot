---
entidad: Infraestructura_Personal
titulo: FabsLabs (Home Lab Server)
tecnologias: [Ubuntu Server, Docker, Cloudflare Tunnel, Portainer, SSH]
rol_rag: Habilidades DevOps, Linux y Redes
---

# Infraestructura y Laboratorio Personal: FabsLabs

## 1. Visión General
Fabián opera y mantiene un entorno de laboratorio local (**Home Lab**) que funciona como su plataforma de experimentación y despliegue para proyectos personales (como el sistema de Telemetría Satelital).
Este entorno simula un servidor de producción real, permitiendo desplegar servicios, bases de datos y APIs en un entorno controlado pero expuesto de forma segura a internet.

## 2. Especificaciones Técnicas

### Sistema Operativo y Gestión
* **OS:** Ubuntu Server (Headless / Sin entorno gráfico).
* **Gestión:** Administración remota exclusiva vía **SSH (Secure Shell)**.
* **Automatización:** Uso de scripts en **Bash** para tareas de mantenimiento y backups.

### Contenerización (Docker)
Todo el software en el laboratorio se ejecuta bajo una arquitectura de microservicios contenerizada:
* **Motor:** Docker Engine + Docker Compose.
* **Orquestación:** Gestión de contenedores, redes y volúmenes persistentes.
* **Monitorización:** Uso de herramientas como **Portainer** para la gestión visual de los recursos del Docker host.

### Redes y Seguridad (Cloudflare)
Para exponer servicios a internet sin comprometer la seguridad de la red local (sin Port Forwarding):
* **Cloudflare Tunnel (cloudflared):** Implementación de túneles cifrados para exponer servicios locales (localhost) hacia dominios públicos HTTPS.
* **Seguridad:** Firewall configurado (UFW), gestión de claves SSH y políticas de acceso Zero Trust.

## 3. Servicios Desplegados (Ejemplos)
El laboratorio aloja actualmente la infraestructura crítica de sus proyectos:
* **Backend de Telemetría:** API Python (Flask) y Base de Datos (SQLite/MariaDB).
* **Broker MQTT:** Servicio de mensajería para dispositivos IoT.
* **Servidores Web:** Nginx/Apache para pruebas de concepto.
* **Portfolio RAG Assistant** Asistente virtual técnico disenado para responder preguntas sobre el portafolio personal.

## 4. Competencias Demostradas
La operación de **FabsLabs** valida competencias prácticas en:
* **Linux SysAdmin:** Gestión de usuarios, permisos, sistema de archivos y procesos (systemd).
* **DevOps Básico:** Ciclo de vida de contenedores e infraestructura como código (Docker Compose).
* **Networking:** Conceptos de DNS, Puertos, Reverse Proxy y Tunelización segura.