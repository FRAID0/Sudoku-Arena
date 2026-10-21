pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '15'))
        timestamps()
        ansiColor('xterm')
        timeout(time: 25, unit: 'MINUTES')
    }

    environment {
        APP_NAME = 'sudoku-arena'
        IMAGE_BACKEND = 'sudoku-backend'
        IMAGE_FRONTEND = 'sudoku-frontend'
        BUILD_TAG = "jenkins-${BUILD_NUMBER}"
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('🔍 Environment & Diagnostics') {
            steps {
                echo "=========================================================="
                echo "🚀 Sudoku Arena — Declarative CI Pipeline"
                echo "Build ID    : ${BUILD_NUMBER}"
                echo "Branch      : ${env.GIT_BRANCH ?: 'local'}"
                echo "Commit      : ${env.GIT_COMMIT ?: 'workspace'}"
                echo "Workspace   : ${WORKSPACE}"
                echo "=========================================================="
                sh 'docker --version'
                sh 'python3 --version'
            }
        }

        stage('🧪 Lint & Manifest Validation') {
            steps {
                echo "📋 Validation du code Python et des manifestes Kubernetes..."
                sh '''
                    python3 -m venv .jenkins_venv
                    . .jenkins_venv/bin/activate
                    pip install --upgrade pip
                    pip install flake8 pyyaml

                    echo "➡️ Analyse statique Flake8 (Backend)..."
                    flake8 backend/app --count --select=E9,F63,F7,F82 --show-source --statistics || true

                    echo "➡️ Validation de la syntaxe des manifestes Kubernetes..."
                    python3 -c "
import yaml, glob, sys
files = sorted(glob.glob('k8s/*.yaml'))
if not files:
    print('⚠️ Aucun fichier YAML trouvé dans k8s/')
for f in files:
    with open(f, 'r') as stream:
        docs = list(yaml.safe_load_all(stream))
        print(f'✅ {f} : {len(docs)} document(s) YAML valide(s)')
"
                '''
            }
        }

        stage('⚡ Unit Tests & JUnit Report') {
            steps {
                echo "🧪 Exécution de la suite de tests unitaires Pytest..."
                sh '''
                    . .jenkins_venv/bin/activate
                    pip install -r backend/requirements.txt
                    mkdir -p reports
                    cd backend
                    python3 -m pytest tests/ -v --junitxml=../reports/test-results.xml
                '''
            }
            post {
                always {
                    junit testResults: 'reports/test-results.xml', allowEmptyResults: false
                }
            }
        }

        stage('🐳 Docker Build') {
            steps {
                echo "🔨 Construction des images Docker multi-conteneurs..."
                sh '''
                    echo "➡️ Build Docker : Backend..."
                    docker build -t ${IMAGE_BACKEND}:${BUILD_TAG} -t ${IMAGE_BACKEND}:latest ./backend

                    echo "➡️ Build Docker : Frontend..."
                    docker build -t ${IMAGE_FRONTEND}:${BUILD_TAG} -t ${IMAGE_FRONTEND}:latest ./frontend

                    echo "📦 Images construites avec succès :"
                    docker images | grep -E "sudoku-backend|sudoku-frontend" | head -n 4
                '''
            }
        }

        stage('🛡️ Security Scan (Trivy)') {
            steps {
                echo "🛡️ Scan de sécurité des vulnérabilités conteneurs (Trivy)..."
                sh '''
                    mkdir -p reports
                    if command -v trivy >/dev/null 2>&1; then
                        echo "➡️ Scan de sécurité de l'image Backend..."
                        trivy image --severity HIGH,CRITICAL --format table --output reports/trivy-backend.txt ${IMAGE_BACKEND}:${BUILD_TAG} || true
                        cat reports/trivy-backend.txt

                        echo "➡️ Scan de sécurité de l'image Frontend..."
                        trivy image --severity HIGH,CRITICAL --format table --output reports/trivy-frontend.txt ${IMAGE_FRONTEND}:${BUILD_TAG} || true
                        cat reports/trivy-frontend.txt
                    else
                        echo "⚠️ Trivy binaire non détecté, exécution via conteneur officiel Trivy..."
                        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                            aquasec/trivy:latest image --severity HIGH,CRITICAL ${IMAGE_BACKEND}:${BUILD_TAG} || true
                        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                            aquasec/trivy:latest image --severity HIGH,CRITICAL ${IMAGE_FRONTEND}:${BUILD_TAG} || true
                    fi
                '''
            }
        }
    }

    post {
        always {
            echo "🧹 Archivage des rapports de tests et de sécurité..."
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            sh 'rm -rf .jenkins_venv reports/test-results.xml'
        }
        success {
            echo "=========================================================="
            echo "🎉 SUCCÈS : Le Pipeline Jenkins Sudoku Arena #${BUILD_NUMBER} a été validé avec brio !"
            echo "=========================================================="
        }
        failure {
            echo "=========================================================="
            echo "❌ ÉCHEC : Le Pipeline Jenkins Sudoku Arena #${BUILD_NUMBER} a échoué."
            echo "Consultez les logs de console et les résultats JUnit ci-dessus."
            echo "=========================================================="
        }
    }
}
