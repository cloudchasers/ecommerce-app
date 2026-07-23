pipeline {
    agent any

    environment {
        IMAGE = '<registry>/ecommerce-app'
        TAG = 'latest'
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

        stage('Build & Unit Test') {
            steps {
                echo 'Install requirements'
                echo 'Run pytest'
                // sh 'pip install -r requirements.txt'
                // sh 'pytest'
            }
        }

        stage('Docker Build & Push') {
            steps {
                echo 'Build Docker image'
                echo 'Push Docker image'
                // sh 'docker build -t $IMAGE:$TAG .'
                // sh 'docker push $IMAGE:$TAG'
            }
        }

        stage('Deploy to Test (ACI)') {
            steps {
                echo 'Deploy to Azure Container Instance'
                // sh './deploy/aci-deploy.sh $IMAGE:$TAG'
            }
        }

        stage('Smoke Test') {
            steps {
                echo 'Run smoke tests'
                // sh 'pytest tests/smoke --base-url=$TEST_URL'
            }
        }

        stage('Approve Prod Deploy') {
            steps {
                input message: 'Deploy to production?'
            }
        }

        stage('Deploy to Prod (K8s)') {
            steps {
                echo 'Deploy to Kubernetes'
                // sh 'kubectl set image deployment/ecommerce-app app=$IMAGE:$TAG'
            }
        }
    }

    post {
        success {
            echo 'Ecommerce pipeline completed successfully'
        }

        failure {
            echo 'Ecommerce pipeline failed'
        }

        always {
            echo 'Pipeline finished'
        }
    }
}
