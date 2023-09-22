# Creating new project
## Backend
```bash
django-admin startproject <project_name>_backend
```
## Frontend
```bash
yarn create react-app <project_name>_frontend --template typescript
cd <project_name>_frontend
yarn add @mui/material @emotion/react @emotion/styled
yarn add react-router-dom
```

### Mobx
```bash
yarn add mobx mobx-react-lite
```

**tsconfig.json**
```
...
"useDefineForClassFields": true,
...
```


## Git
```bash
git init
```