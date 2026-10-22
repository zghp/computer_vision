#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QString>

QT_BEGIN_NAMESPACE

namespace Ui {
class MainWindow;
}

QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

private slots:
    void on_btnSource_clicked();
    void on_btnDestination_clicked();
    void on_btnExecute_clicked();

private:
    Ui::MainWindow *ui;
    QString sourceFolder;
    QString destinationFolder;
};
#endif // MAINWINDOW_H
