/**
 * Toast notification utilities
 * Wrapper cho sonner toast library với error handling chuẩn production
 */

import { toast } from "sonner"
import { ApiError, NetworkError, TimeoutError } from "./api"

/**
 * Hiển thị error toast với message phù hợp
 */
export function showError(error: unknown, defaultMessage?: string): void {
  let message = defaultMessage || "Đã xảy ra lỗi"

  if (error instanceof ApiError) {
    message = error.message || `Lỗi API: ${error.statusCode || "Unknown"}`
    
    // Custom messages cho các status codes phổ biến
    if (error.statusCode === 404) {
      message = "Không tìm thấy dữ liệu"
    } else if (error.statusCode === 401 || error.statusCode === 403) {
      message = "Không có quyền truy cập"
    } else if (error.statusCode === 429) {
      message = "Quá nhiều yêu cầu. Vui lòng thử lại sau"
    } else if (typeof error.statusCode === "number" && error.statusCode >= 500) {
      message = "Lỗi server. Vui lòng thử lại sau"
    }
  } else if (error instanceof NetworkError) {
    message = error.message || "Không thể kết nối đến server"
  } else if (error instanceof TimeoutError) {
    message = "Request timeout. Vui lòng thử lại"
  } else if (error instanceof Error) {
    message = error.message
  } else if (typeof error === "string") {
    message = error
  }

  toast.error(message, {
    duration: 5000,
    description: error instanceof ApiError && error.endpoint 
      ? `Endpoint: ${error.endpoint}` 
      : undefined,
  })
}

/**
 * Hiển thị success toast
 */
export function showSuccess(message: string, description?: string): void {
  toast.success(message, {
    duration: 3000,
    description,
  })
}

/**
 * Hiển thị info toast
 */
export function showInfo(message: string, description?: string): void {
  toast.info(message, {
    duration: 4000,
    description,
  })
}

/**
 * Hiển thị warning toast
 */
export function showWarning(message: string, description?: string): void {
  toast.warning(message, {
    duration: 4000,
    description,
  })
}

/**
 * Hiển thị loading toast và trả về dismiss function
 */
export function showLoading(message: string): () => void {
  const toastId = toast.loading(message)
  return () => toast.dismiss(toastId)
}

