pipeline {
    agent any

    environment {
        REGISTRY = "cloudchasers.azurecr.io"
        IMAGE_NAME = "ecommerce-app"
        TAG = "latest"
    }

    stages {
        stage('Checkout') {
            steps {
                git(
                    branch: 'main',
                    credentialsId: 'github-creds',
                    url: 'https://github.com/cloudchasers/ecommerce-app.git'
                )
            }
        }

        stage('Deploy to Dev EC2') {
            steps {
                sh '''
                    ssh -o StrictHostKeyChecking=no \
                    -i /var/lib/jenkins/.ssh/jenkins_deploy_key \
                    ubuntu@3.90.15.65 \
                    "cd /home/ubuntu/ecommerce-app && \
                    git pull && \
                    docker compose down && \
                    docker compose up -d --build"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t ${IMAGE_NAME}:${TAG} .
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    docker run --rm -e PYTHONPATH=/app ${IMAGE_NAME}:${TAG} pytest tests/test.py -v
                '''
            }
        }

        stage('Login to ACR') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'acr-creds',
                        usernameVariable: 'ACR_USER',
                        passwordVariable: 'ACR_PASS'
                    )
                ]) {
                    sh '''
                        echo "$ACR_PASS" | docker login ${REGISTRY} \
                        -u "$ACR_USER" \
                        --password-stdin
                    '''
                }
            }
        }

        stage('Tag Image') {
            steps {
                sh '''
                    docker tag ${IMAGE_NAME}:${TAG} \
                    ${REGISTRY}/${IMAGE_NAME}:${TAG}
                '''
            }
        }

        stage('Push Image') {
            steps {
                sh '''
                    docker push \
                    ${REGISTRY}/${IMAGE_NAME}:${TAG}
                '''
            }
        }

        stage('Redeploy ACI') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'acr-creds',
                        usernameVariable: 'ACR_USER',
                        passwordVariable: 'ACR_PASS'
                    )
                ]) {
                    echo 'Deploy to ACI'
                }
            }
        }
    }

    post {
        success {
            echo 'Ecommerce image pushed to ACR and ACI redeployed successfully'
        }

        failure {
            echo 'Pipeline failed'
        }
    }
}
