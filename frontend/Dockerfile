FROM nginx:alpine

# Remplacer la configuration par défaut par la nôtre
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copier les fichiers statiques de l'application Web
COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
