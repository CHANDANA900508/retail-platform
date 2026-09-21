pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOYMENT_ACTION',
            choices: ['DEPLOY', 'ROLLBACK'],
            description: 'Select deployment action'
        )

        choice(
            name: 'ENVIRONMENT',
            choices: ['UAT', 'PRODUCTION'],
            description: 'Select deployment environment'
        )

        string(
            name: 'VERSION',
            defaultValue: '4.2.1',
            description: 'Version to deploy, for example 4.2.1'
        )

        choice(
            name: 'CONFIRM_PROD',
            choices: ['NO', 'YES'],
            description: 'Production deployment confirmation'
        )
    }

    environment {
        IMAGE_NAME = 'retail-app'
        APP_PORT = '8081'
    }

    stages {

        stage('Validate Parameters') {
            steps {
                script {
                    echo "======================================"
                    echo "Deployment Action : ${params.DEPLOYMENT_ACTION}"
                    echo "Environment       : ${params.ENVIRONMENT}"
                    echo "Requested Version : ${params.VERSION}"
                    echo "Production Confirm: ${params.CONFIRM_PROD}"
                    echo "======================================"

                    if (params.ENVIRONMENT == 'PRODUCTION' &&
                        params.CONFIRM_PROD != 'YES') {
                        error("Production deployment blocked: CONFIRM_PROD must be YES")
                    }

                    if (params.VERSION.trim() == '') {
                        error("VERSION cannot be empty")
                    }
                }
            }
        }

        stage('Validate Git Version') {
            steps {
                bat "git fetch --tags --force origin"
                script {
                    def tagExists = bat(
                        script: "git ls-remote --tags origin refs/tags/v${params.VERSION}",
                        returnStdout: true
                    ).trim()

                    if (tagExists == "") {
                        error("Git tag v${params.VERSION} does not exist")
                    }

                    def commit = bat(
                        script: "git rev-list -n 1 v${params.VERSION}",
                        returnStdout: true
                    ).trim()

                    echo "Selected Git tag : v${params.VERSION}"
                    echo "Selected Git commit: ${commit}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                bat "docker build -t ${IMAGE_NAME}:${params.VERSION} ."
            }
        }

        stage('Deploy') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY'
                }
            }

            steps {
                script {

                    def oldContainer = bat(
                        script: "docker ps -q -f name=retail-app-prod",
                        returnStdout: true
                    ).trim()

                    
                    

                    echo "Previous production container: ${oldContainer ?: 'NONE'}"
                    echo "Previous production image    : ${oldImage}"

                    writeFile(
                        file: 'previous-production.txt',
                        text: oldImage
                    )

                    bat """
                        docker rm -f retail-app-candidate 2>NUL || exit /b 0
                        docker run -d --name retail-app-candidate ^
                          -p 8082:8081 ^
                          -e APP_VERSION=${params.VERSION} ^
                          -e APP_ENV=${params.ENVIRONMENT} ^
                          -e PAYMENT_STATUS=FIXED ^
                          ${IMAGE_NAME}:${params.VERSION}
                    """

                    echo "Candidate ${IMAGE_NAME}:${params.VERSION} started on port 8082"

                    bat """
                        powershell -Command "Start-Sleep -Seconds 15"
                        docker inspect -f "{{.State.Health.Status}}" retail-app-candidate
                    """

                    def health = bat(
                        script: 'docker inspect -f "{{.State.Health.Status}}" retail-app-candidate',
                        returnStdout: true
                    ).trim()

                    echo "Candidate health status: ${health}"

                    if (health != 'healthy') {
                        echo "Candidate health check FAILED"
                        bat "docker rm -f retail-app-candidate"
                        rollbackProduction(oldImage)
                        error("Deployment failed: candidate health check failed. Automatic rollback completed.")
                    }

                    echo "Candidate health check PASSED"

                    if (oldContainer) {
                        bat "docker rm -f retail-app-prod"
                    }

                    bat """
                        docker run -d --name retail-app-prod ^
                          -p 8081:8081 ^
                          -e APP_VERSION=${params.VERSION} ^
                          -e APP_ENV=${params.ENVIRONMENT} ^
                          -e PAYMENT_STATUS=FIXED ^
                          ${IMAGE_NAME}:${params.VERSION}
                    """

                    bat "docker rm -f retail-app-candidate"

                    bat """
                        powershell -Command "Start-Sleep -Seconds 10"
                    """

                    def finalHealth = bat(
                        script: 'docker inspect -f "{{.State.Health.Status}}" retail-app-prod',
                        returnStdout: true
                    ).trim()

                    echo "Final production health: ${finalHealth}"
                    echo "Old production image: ${oldImage}"
                    echo "New production image: ${IMAGE_NAME}:${params.VERSION}"

                    if (finalHealth != 'healthy') {
                        echo "FINAL HEALTH CHECK FAILED"
                        rollbackProduction(oldImage)
                        error("Production deployment failed. Automatic rollback completed.")
                    }

                    echo "Production deployment successful."
                }
            }
        }

        stage('Rollback') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'ROLLBACK'
                }
            }

            steps {
                script {
                    def previousImage = 'NONE'

                    if (fileExists('previous-production.txt')) {
                        previousImage = readFile('previous-production.txt').trim()
                    }

                    if (previousImage == 'NONE' || previousImage == '') {
                        error("No previous production image is recorded.")
                    }

                    echo "Rolling back to: ${previousImage}"

                    bat "docker rm -f retail-app-prod 2>NUL || exit /b 0"

                    bat """
                        docker run -d --name retail-app-prod ^
                          -p 8081:8081 ^
                          -e APP_VERSION=${previousImage.split(':')[-1]} ^
                          -e APP_ENV=PRODUCTION ^
                          -e PAYMENT_STATUS=FIXED ^
                          ${previousImage}
                    """

                    bat "powershell -Command \"Start-Sleep -Seconds 10\""

                    def rollbackHealth = bat(
                        script: 'docker inspect -f "{{.State.Health.Status}}" retail-app-prod',
                        returnStdout: true
                    ).trim()

                    echo "Rollback health: ${rollbackHealth}"

                    if (rollbackHealth != 'healthy') {
                        error("Rollback failed: restored production container is unhealthy")
                    }

                    echo "Rollback completed successfully."
                }
            }
        }
    }

    post {
        success {
            echo "FINAL STATE: SUCCESS"
        }

        failure {
            echo "FINAL STATE: FAILURE"
        }
    }
}

def rollbackProduction(String oldImage) {

    if (oldImage == 'NONE' || oldImage == '') {
        error("Automatic rollback cannot proceed because no previous production image was recorded.")
    }

    echo "AUTOMATIC ROLLBACK"
    echo "Restoring previous production image: ${oldImage}"

    bat "docker rm -f retail-app-prod 2>NUL || exit /b 0"

    def oldVersion = oldImage.substring(oldImage.lastIndexOf(':') + 1)

    bat """
        docker run -d --name retail-app-prod ^
          -p 8081:8081 ^
          -e APP_VERSION=${oldVersion} ^
          -e APP_ENV=PRODUCTION ^
          -e PAYMENT_STATUS=FIXED ^
          ${oldImage}
    """

    bat "powershell -Command \"Start-Sleep -Seconds 10\""

    def rollbackHealth = bat(
        script: 'docker inspect -f "{{.State.Health.Status}}" retail-app-prod',
        returnStdout: true
    ).trim()

    echo "Rollback health status: ${rollbackHealth}"

    if (rollbackHealth != 'healthy') {
        error("AUTOMATIC ROLLBACK FAILED")
    }

    echo "AUTOMATIC ROLLBACK COMPLETED"
}