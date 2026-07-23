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

        stage('Deploy-Dev') {
            steps {
                sh '''
                ssh -i ~/.ssh/jenkins_deploy_key ubuntu@54.227.120.126 \
                "cd /home/ubuntu/ecommerce-app && git pull"
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
