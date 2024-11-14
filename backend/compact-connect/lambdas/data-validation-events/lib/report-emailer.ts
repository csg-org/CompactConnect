import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { renderToStaticMarkup, TReaderDocument } from '@usewaypoint/email-builder';
import { EnvironmentVariablesService } from './environment-variables-service';

const environmentVariableService = new EnvironmentVariablesService();

interface ReportEmailerProperties {
    logger: Logger;
    sesClient: SESClient;
}


export class ReportEmailer {
    logger: Logger;
    sesClient: SESClient;
    emailTemplate: TReaderDocument = {
        'root': {
            'type': 'EmailLayout',
            'data': {
                'backdropColor': '#E9EFF9',
                'canvasColor': '#FFFFFF',
                'textColor': '#242424',
                'fontFamily': 'MODERN_SANS',
                'childrenIds': [
                    'block-logo',
                    'block-header',
                    'block-sub-heading',
                    'block-ingest-error',
                    'block-div',
                    'block-license-type',
                    'block-footer'
                ]
            }
        },
        'block-logo': {
            'type': 'Image',
            'data': {
                'style': {
                    'padding': {
                        'top': 40,
                        'bottom': 8,
                        'right': 68,
                        'left': 68
                    },
                    'backgroundColor': null,
                    'textAlign': 'center'
                },
                'props': {
                    'width': null,
                    'height': 100,
                    'url': 'https://compactconnect.org/wp-content/uploads/2024/07/Compact-Connect-logo_FINAL.png',
                    'alt': '',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        },
        'block-footer': {
            'type': 'Text',
            'data': {
                'style': {
                    'color': '#ffffff',
                    'backgroundColor': '#2459A9',
                    'fontSize': 13,
                    'fontFamily': 'MODERN_SANS',
                    'fontWeight': 'normal',
                    'textAlign': 'center',
                    'padding': {
                        'top': 40,
                        'bottom': 40,
                        'right': 68,
                        'left': 68
                    }
                },
                'props': {
                    'text': '© 2024 CompactConnect'
                }
            }
        },
        'block-header': {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': 'License Data Error Summary',
                    'level': 'h1'
                },
                'style': {
                    'textAlign': 'center',
                    'padding': {
                        'top': 28,
                        'bottom': 12,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        },
        'block-sub-heading': {
            'type': 'Text',
            'data': {
                'style': {
                    'fontSize': 18,
                    'fontWeight': 'normal',
                    'textAlign': 'center',
                    'padding': {
                        'top': 0,
                        'bottom': 52,
                        'right': 40,
                        'left': 40
                    }
                },
                'props': {
                    'text': 'There have been some license data errors that prevented ingest. They are listed below:'
                }
            }
        },
        'block-ingest-error': {
            'type': 'ColumnsContainer',
            'data': {
                'style': {
                    'padding': {
                        'top': 4,
                        'bottom': 12,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'columnsCount': 2,
                    'columnsGap': 16,
                    'columns': [
                        {
                            'childrenIds': [
                                'block-ingest-error-a',
                                'block-ingest-error-b'
                            ]
                        },
                        {
                            'childrenIds': [
                                'block-ingest-error-c'
                            ]
                        },
                        {
                            'childrenIds': []
                        }
                    ]
                }
            }
        },
        'block-ingest-error-a': {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': 'Ingest error',
                    'level': 'h3'
                },
                'style': {
                    'color': '#DA2525',
                    'padding': {
                        'top': 0,
                        'bottom': 4,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        },
        'block-ingest-error-b': {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': "'utf-8' codec can't decode byte 0x83 in position 0: invalid start byte"
                }
            }
        },
        'block-ingest-error-c': {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': ''
                }
            }
        },
        'block-license-type': {
            'type': 'ColumnsContainer',
            'data': {
                'style': {
                    'padding': {
                        'top': 4,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'columnsCount': 2,
                    'columnsGap': 16,
                    'contentAlignment': 'top',
                    'columns': [
                        {
                            'childrenIds': [
                                'block-license-typea',
                                'block-license-typeb'
                            ]
                        },
                        {
                            'childrenIds': [
                                'block-license-typec',
                                'block-license-typed'
                            ]
                        },
                        {
                            'childrenIds': []
                        }
                    ]
                }
            }
        },
        'block-license-typea': {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': 'Line 1',
                    'level': 'h3'
                },
                'style': {
                    'color': '#2459A9',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        },
        'block-license-typeb': {
            'type': 'Text',
            'data': {
                'style': {
                    'color': null,
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'markdown': true,
                    'text': "licenseType: 'licenseType' must be one of ['occupational therapist', 'occupational therapy assistant']",
                }
            }
        },
        'block-license-typec': {
            'type': 'Text',
            'data': {
                'style': {
                    'color': '#A3A3A3',
                    'fontSize': 14,
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'markdown': true,
                    'text': 'PRACTITIONER INFO'
                }
            }
        },
        'block-license-typed': {
            'type': 'Text',
            'data': {
                'style': {
                    'color': null,
                    'fontSize': 16,
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'markdown': true,
                    'text': 'First name: Example\nLast name: Example\nBirthdate: Example'
                }
            }
        },
        'block-div': {
            'type': 'Divider',
            'data': {
                'style': {
                    'padding': {
                        'top': 12,
                        'bottom': 16,
                        'right': 0,
                        'left': 0
                    }
                },
                'props': {
                    'lineColor': '#CCCCCC'
                }
            }
        },
    };

    public constructor(props: ReportEmailerProperties) {
        this.logger = props.logger;
        this.sesClient = props.sesClient;
    }

    public generateReport(events: any[]): string {
        return renderToStaticMarkup(this.emailTemplate, { rootBlockId: 'root' });
    }

    public async sendReportEmail(events: any[]) {
        // Generate the HTML report
        const htmlContent = this.generateReport(events);

        try {
            // Send the email
            const command = new SendEmailCommand({
                Destination: {
                    // TODO: Get addressee from config
                    ToAddresses: ['justin@inspiringapps.com'],
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: htmlContent
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Data Validation Report'
                    }
                },
                // We're required by the IAM policy to use this display name
                Source: `Compact Connect <${environmentVariableService.getFromAddress()}>`,
            });

            return (await this.sesClient.send(command)).MessageId;
        } catch (error) {
            this.logger.error('Error sending email:', { error: error });
            throw error;
        }
    }
}
