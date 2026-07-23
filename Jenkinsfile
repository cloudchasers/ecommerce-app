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

        stage('Run Tests') {
            steps {
                sh '''
                    pip install -r requirements.txt
                    pytest tests/test.py
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
    }

    post {
        success {
            echo 'Ecommerce image pushed to ACR successfully'
        }

        failure {
            echo 'Pipeline failed'
        }
    }
}
