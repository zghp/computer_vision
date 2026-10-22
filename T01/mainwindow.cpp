#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QFileDialog>
#include <QMessageBox>

#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>

#include <filesystem>

namespace fs = std::filesystem;


/**
 * @brief Builds the window and sets the default flip option.
 */
MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    ui->radioHorizontal->setChecked(true);   // horizontal flip is the default
}


/**
 * @brief Frees the memory used by the generated UI.
 */
MainWindow::~MainWindow()
{
    delete ui;
}


/**
 * @brief Lets the user choose the source folder (the one with the pictures).
 *
 * The path is stored in sourceFolder and shown in lblSource.
 * If the user presses Cancel, nothing changes.
 */
void MainWindow::on_btnSource_clicked()
{
    QString dir = QFileDialog::getExistingDirectory(this, tr("Alege folderul sursa"));
    if (dir.isEmpty())
        return; // user pressed Cancel

    sourceFolder = dir;
    ui->lblSource->setText(dir);
}


/**
 * @brief Lets the user choose the destination folder.
 *
 *The path is stored in destinationFolder and shown in lblDestination.
 */
void MainWindow::on_btnDestination_clicked()
{
    QString dir = QFileDialog::getExistingDirectory(this, tr("Alege folderul destinatie"));
    if (dir.isEmpty())
        return;

    destinationFolder = dir;
    ui->lblDestination->setText(dir);
}


/**
 * @brief Flips every picture from the source folder and saves it in the
 *        destination folder under the same name.
 *
 * Steps:
 *  1. Check that both folders are selected and that they are different.
 *  2. Read the selected radio button and convert it to a cv::flip code.
 *  3. Go through all files of the source folder.
 *  4. Files that are not images are skipped; images are flipped and saved.
 *  5. Show how many files were processed and how many were skipped.
 */
void MainWindow::on_btnExecute_clicked()
{
    // 1. both folders must be selected
    if (sourceFolder.isEmpty() || destinationFolder.isEmpty())
    {
        QMessageBox::warning(this, tr("Atentie"),
                             tr("Selecteaza folderul sursa si folderul destinatie."));
        return;
    }

    fs::path src = fs::u8path(sourceFolder.toStdString());
    fs::path dst = fs::u8path(destinationFolder.toStdString());

    // same folder would overwrite the original pictures
    if (fs::equivalent(src, dst))
    {
        QMessageBox::warning(this, tr("Atentie"),
                             tr("Folderul destinatie trebuie sa fie diferit de cel sursa."));
        return;
    }

    // 2. flip code for cv::flip: 1 = horizontal, 0 = vertical, -1 = both
    int flipCode = -1;
    if (ui->radioHorizontal->isChecked())    flipCode = 1;
    else if (ui->radioVertical->isChecked()) flipCode = 0;

    int done = 0, skipped = 0;

    // 3. file names are read from the folder
    for (const auto &entry : fs::directory_iterator(src))
    {
        if (!entry.is_regular_file())
        {
            ++skipped;
            continue;
        }

        // 4. imread returns an empty image if the file is not a picture
        cv::Mat image = cv::imread(entry.path().string());
        if (image.empty())
        {
            ++skipped;
            continue;
        }

        cv::Mat flipped;
        cv::flip(image, flipped, flipCode);

        // same file name, saved in the destination folder
        fs::path out = dst / entry.path().filename();
        if (cv::imwrite(out.string(), flipped))
            ++done;
        else
            ++skipped;
    }

    // 5. report the result
    ui->lblStatus->setText(tr("All done: %1 poze oglindite, %2 fisiere ignorate.")
                               .arg(done).arg(skipped));
}