
## The QR Code Package stopped working - probably after R Version 3.5?
## The problem is the call data(qrCodeSpec, envir = environment()) that lacks
## a package='qrcode'.
## Here are copied version of the codes, where there is a fixed line.

#' @importFrom utils data head
qrcode_gen_patch <- function (dataString, ErrorCorrectionLevel = "L", dataOutput = FALSE,
  plotQRcode = TRUE, wColor = "White", bColor = "black", mask = 1,
  softLimitFlag = TRUE)
{
  qrInfo <- qrcode_qrVersionInfo_patch(dataString, ECLevel = ErrorCorrectionLevel)
  if (qrInfo$Version > 10 & softLimitFlag) {
    warning("Input string size too big. Try lower Error Correction Level or shortern the input string.")
  }
  else {
    data <- qrcode:::qrInitMatrix(qrInfo$Version)
    dataPoly <- qrcode::DataStringBinary(dataString, qrInfo)
    poly <- qrcode:::polynomialGenerator(qrInfo$ECwordPerBlock)
    allBinary <- qrcode::qrInterleave(poly, dataPoly, qrInfo)
    data <- qrcode::qrFillUpMatrix(allBinary, data, qrInfo$Version)
    dataMasked <- qrcode::qrMask(data, qrInfo, mask)
    if (plotQRcode) {
      stats::heatmap(dataMasked[nrow(dataMasked):1, ], Rowv = NA,
        Colv = NA, scale = "none", col = c(wColor, bColor),
        labRow = "", labCol = "")
    }
    if (dataOutput) {
      return(dataMasked)
    }
  }
}

qrcode_qrVersionInfo_patch <- function (dataString, ECLevel = "L")
{
  if (max(ECLevel == c("L", "M", "Q", "H")) == 0) {
    warning("Wrong ECLevel. Allowed value are  \"L\",\"M\",\"Q\" and \"H\"")
  }
  qrCodeSpec <- ""
  # Fix for original
  #     data(qrCodeSpec, envir = environment())
  # is the following
  data(qrCodeSpec, envir = environment(), package='qrcode')

  if (length(grep("[a-z!?><;@#&()]", dataString)) == 0) {
    mode <- "0010"
    qrInfo <- head(qrCodeSpec[(qrCodeSpec$ECL == ECLevel &
      qrCodeSpec$Alphanumeric >= nchar(dataString)), c(1:2,
      4, 6:11)], 1)
  }
  else {
    mode <- "0100"
    qrInfo <- head(qrCodeSpec[(qrCodeSpec$ECL == ECLevel &
      qrCodeSpec$Byte >= nchar(dataString)), c(1:2, 5:11)],
      1)
  }
  qrInfo$mode <- mode
  return(qrInfo)
}


