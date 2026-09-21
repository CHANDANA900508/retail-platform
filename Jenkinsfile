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
                bat 'git fetch --tags --force origin'

                script {
                    def tagExists = bat(
                        script: "@echo off\ngit ls-remote --tags origin refs/tags/v${params.VERSION}",
                        returnStdout: true
                    ).trim()

                    if (tagExists == "") {
                        error("Git tag v${params.VERSION} does not exist")
                    }

                    def commit = bat(
                        script: "@echo off\ngit rev-list -n 1 v${params.VERSION}",
                        returnStdout: true
                    ).trim()

                    echo "Selected Git tag    : v${params.VERSION}"
                    echo "Selected Git commit : ${commit}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                bat """
                    docker build ^
                      --build-arg APP_VERSION=${params.VERSION} ^
                      -t ${IMAGE_NAME}:${params.VERSION} .
                """
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

                    /*
                     * Find currently running production container.
                     * @echo off prevents Jenkins from capturing the
                     * command itself in returnStdout.
                     */
                    def oldContainer = bat(
                        script: '@echo off\ndocker ps -q -f "name=^retail-app-prod$"',
                        returnStdout: true
                    ).trim()

                    def oldImage = 'NONE'

                    if (oldContainer) {
                        oldImage = bat(
                            script: '@echo off\ndocker inspect -f "{{.Config.Image}}" retail-app-prod',
                            returnStdout: true
                        ).trim()
                    }

                    echo "======================================"
                    echo "OLD PRODUCTION CONTAINER : ${oldContainer ?: 'NONE'}"
                    echo "OLD PRODUCTION IMAGE     : ${oldImage}"
                    echo "NEW PRODUCTION IMAGE     : ${IMAGE_NAME}:${params.VERSION}"
                    echo "======================================"

                    /*
                     * Record the old production image.
                     */
                    writeFile(
                        file: 'previous-production.txt',
                        text: oldImage
                    )

                    /*
                     * Start candidate FIRST.
                     * Old production is still running.
                     */
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

                    /*
                     * Wait for Docker health check.
                     */
                    
                     sleep(time: 15,unit: 'SECONDS')

                    def health = bat(
                        script: '@echo off\ndocker inspect -f "{{.State.Health.Status}}" retail-app-candidate',
                        returnStdout: true
                    ).trim()

                    echo "Candidate health status: ${health}"

                    /*
                     * If candidate is unhealthy, rollback.
                     */
                    if (health != 'healthy') {

                        echo "======================================"
                        echo "CANDIDATE HEALTH CHECK FAILED"
                        echo "Starting automatic rollback..."
                        echo "======================================"

                        bat "docker rm -f retail-app-candidate 2>NUL || exit /b 0"

                        if (oldImage != 'NONE' && oldImage != '') {
                            rollbackProduction(oldImage)
                        } else {
                            echo "No previous production image exists."
                            echo "This is the first deployment."
                        }

                        error("Deployment failed. Automatic rollback was required.")
                    }

                    echo "Candidate health check PASSED"

                    /*
                     * NEW candidate is healthy.
                     * Now old production can be removed.
                     */
                    if (oldContainer) {
                        echo "Removing old production container..."
                        bat "docker rm -f retail-app-prod"
                    }

                    /*
                     * Start NEW production version.
                     */
                    bat """
                        docker run -d --name retail-app-prod ^
                          -p 8081:8081 ^
                          -e APP_VERSION=${params.VERSION} ^
                          -e APP_ENV=${params.ENVIRONMENT} ^
                          -e PAYMENT_STATUS=FIXED ^
                          ${IMAGE_NAME}:${params.VERSION}
                    """

                    echo "New production version started."

                    /*
                     * Candidate is no longer required.
                     */
                    bat "docker rm -f retail-app-candidate 2>NUL || exit /b 0"

                    /*
                     * Final production health check.
                     */
                    sleep(time: 10, unit: 'SECONDS')

                    def finalHealth = bat(
                        script: '@echo off\ndocker inspect -f "{{.State.Health.Status}}" retail-app-prod',
                        returnStdout: true
                    ).trim()

                    echo "======================================"
                    echo "OLD VERSION   : ${oldImage}"
                    echo "NEW VERSION   : ${IMAGE_NAME}:${params.VERSION}"
                    echo "FINAL HEALTH  : ${finalHealth}"
                    echo "======================================"

                    /*
                     * If final production health check fails,
                     * automatically restore old production image.
                     */
                    if (finalHealth != 'healthy') {

                        echo "FINAL HEALTH CHECK FAILED"
                        echo "Starting automatic rollback..."

                        if (oldImage != 'NONE' && oldImage != '') {
                            rollbackProduction(oldImage)
                        } else {
                            echo "No previous production image available."
                        }

                        error("Production deployment failed. Automatic rollback was required.")
                    }

                    echo "======================================"
                    echo "PRODUCTION DEPLOYMENT SUCCESSFUL"
                    echo "OLD VERSION : ${oldImage}"
                    echo "NEW VERSION : ${IMAGE_NAME}:${params.VERSION}"
                    echo "FINAL STATE : SUCCESS"
                    echo "======================================"
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

                    echo "======================================"
                    echo "MANUAL ROLLBACK"
                    echo "Restoring: ${previousImage}"
                    echo "======================================"

                    bat "docker rm -f retail-app-prod 2>NUL || exit /b 0"

                    def previousVersion =
                        previousImage.substring(previousImage.lastIndexOf(':') + 1)

                    bat """
                        docker run -d --name retail-app-prod ^
                          -p 8081:8081 ^
                          -e APP_VERSION=${previousVersion} ^
                          -e APP_ENV=PRODUCTION ^
                          -e PAYMENT_STATUS=FIXED ^
                          ${previousImage}
                    """

                    bat """
                        powershell -Command "Start-Sleep -Seconds 10"
                    """

                    def rollbackHealth = bat(
                        script: '@echo off\ndocker inspect -f "{{.State.Health.Status}}" retail-app-prod',
                        returnStdout: true
                    ).trim()

                    echo "Rollback health: ${rollbackHealth}"

                    if (rollbackHealth != 'healthy') {
                        error("Rollback failed: restored production container is unhealthy")
                    }

                    echo "======================================"
                    echo "ROLLBACK COMPLETED SUCCESSFULLY"
                    echo "RESTORED VERSION : ${previousVersion}"
                    echo "FINAL STATE      : SUCCESS"
                    echo "======================================"
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


/*
 * Automatic rollback function
 */
def rollbackProduction(String oldImage) {

    if (oldImage == 'NONE' || oldImage == '') {
        error("Automatic rollback cannot proceed because no previous production image was recorded.")
    }

    echo "======================================"
    echo "AUTOMATIC ROLLBACK"
    echo "Restoring previous image: ${oldImage}"
    echo "======================================"

    bat "docker rm -f retail-app-prod 2>NUL || exit /b 0"

    def oldVersion =
        oldImage.substring(oldImage.lastIndexOf(':') + 1)

    bat """
        docker run -d --name retail-app-prod ^
          -p 8081:8081 ^
          -e APP_VERSION=${oldVersion} ^
          -e APP_ENV=PRODUCTION ^
          -e PAYMENT_STATUS=FIXED ^
          ${oldImage}
    """

    bat """
        powershell -Command "Start-Sleep -Seconds 10"
    """

    def rollbackHealth = bat(
        script: '@echo off\ndocker inspect -f "{{.State.Health.Status}}" retail-app-prod',
        returnStdout: true
    ).trim()

    echo "Rollback health status: ${rollbackHealth}"

    if (rollbackHealth != 'healthy') {
        error("AUTOMATIC ROLLBACK FAILED")
    }

    echo "AUTOMATIC ROLLBACK COMPLETED"
}